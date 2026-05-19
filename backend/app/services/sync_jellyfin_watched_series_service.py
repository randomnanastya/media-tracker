from sqlalchemy import insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.jellyfin_client import (
    fetch_jellyfin_episodes_for_user_all,
    fetch_jellyfin_series_by_ids,
)
from app.config import logger
from app.models.media import Episode, Season, Series
from app.models.schedule import ServiceType
from app.models.user import User, WatchHistory, WatchStatus
from app.schemas.jellyfin import JellyfinWatchedSeriesResponse
from app.services.series_utils import resolve_series_from_indexes
from app.services.service_config_repository import get_decrypted_config
from app.utils.datetime import parse_datetime


async def sync_jellyfin_watched_series(session: AsyncSession) -> JellyfinWatchedSeriesResponse:
    """
    Sync watched episodes from Jellyfin for all users.
    """
    config = await get_decrypted_config(session, ServiceType.JELLYFIN)
    if config is None:
        logger.info("Jellyfin is not configured, skipping watched series sync")
        return JellyfinWatchedSeriesResponse()
    url, api_key = config

    # 1. Get all users with jellyfin_user_id
    users_result = await session.execute(select(User).where(User.jellyfin_user_id.isnot(None)))
    users = users_result.scalars().all()

    total_users = len(users)
    total_episodes_processed = 0
    watched_added = 0
    watched_updated = 0
    unwatched_marked = 0

    logger.info("Starting watched episodes sync for %s users", total_users)
    for user in users:
        user_added = user_updated = user_unwatched = 0

        if not user.jellyfin_user_id:
            continue

        logger.info("Processing episodes for user %s", user.username)

        try:
            # Step 1: get flat list of episodes from Jellyfin
            episodes_data = await fetch_jellyfin_episodes_for_user_all(
                url, api_key, user.jellyfin_user_id
            )

            if not episodes_data:
                logger.info("No episodes found for user %s", user.username)
                continue

            # Step 2: collect unique jellyfin series IDs from episodes
            series_jellyfin_ids = list(
                {ep["SeriesId"] for ep in episodes_data if ep.get("SeriesId")}
            )

            # Step 3: fetch provider IDs for those series from Jellyfin
            series_items = await fetch_jellyfin_series_by_ids(
                url, api_key, user.jellyfin_user_id, series_jellyfin_ids
            )
            series_provider_ids: dict[str, dict[str, str]] = {}
            for item in series_items:
                jf_id = item.get("Id")
                if jf_id:
                    series_provider_ids[jf_id] = item.get("ProviderIds", {}) or {}

            # Step 4: load Series from DB in a single query
            tvdb_ids = {v.get("Tvdb") for v in series_provider_ids.values() if v.get("Tvdb")}
            imdb_ids = {v.get("Imdb") for v in series_provider_ids.values() if v.get("Imdb")}
            jf_ids_set = set(series_jellyfin_ids)

            series_result = await session.execute(
                select(Series).where(
                    or_(
                        Series.jellyfin_id.in_(jf_ids_set),
                        Series.tvdb_id.in_(tvdb_ids),
                        Series.imdb_id.in_(imdb_ids),
                    )
                )
            )
            db_series_list = series_result.scalars().all()

            by_jf_id: dict[str, Series] = {
                s.jellyfin_id: s for s in db_series_list if s.jellyfin_id
            }
            by_tvdb_id: dict[str, Series] = {s.tvdb_id: s for s in db_series_list if s.tvdb_id}
            by_imdb_id: dict[str, Series] = {s.imdb_id: s for s in db_series_list if s.imdb_id}

            # Step 5: resolve each jellyfin_series_id to a Series object with heal
            series_by_jellyfin_series_id: dict[str, Series] = {}
            unmatched_series_ids: set[str] = set()

            for jf_sid in series_jellyfin_ids:
                pids = series_provider_ids.get(jf_sid, {})
                tvdb = pids.get("Tvdb")
                imdb = pids.get("Imdb")

                series = resolve_series_from_indexes(
                    jellyfin_id=jf_sid,
                    tvdb_id=tvdb,
                    imdb_id=imdb,
                    by_jellyfin_id=by_jf_id,
                    by_tvdb_id=by_tvdb_id,
                    by_imdb_id=by_imdb_id,
                )
                if not series:
                    if jf_sid not in unmatched_series_ids:
                        logger.warning(
                            "Series not found: jellyfin_series_id=%s tvdb=%s imdb=%s",
                            jf_sid,
                            tvdb,
                            imdb,
                        )
                        unmatched_series_ids.add(jf_sid)
                    continue

                # heal Series.jellyfin_id
                if series.jellyfin_id != jf_sid:
                    logger.info(
                        "Healing Series.jellyfin_id: id=%s old=%s new=%s",
                        series.id,
                        series.jellyfin_id,
                        jf_sid,
                    )
                    series.jellyfin_id = jf_sid
                    by_jf_id[jf_sid] = series

                series_by_jellyfin_series_id[jf_sid] = series

            # Step 6: load seasons and episodes for resolved series
            resolved_series = list(series_by_jellyfin_series_id.values())
            resolved_series_ids = [s.id for s in resolved_series]

            seasons_result = await session.execute(
                select(Season).where(Season.series_id.in_(resolved_series_ids))
            )
            seasons = seasons_result.scalars().all()

            episodes_result = await session.execute(
                select(Episode)
                .options(selectinload(Episode.season))
                .where(Episode.season_id.in_([s.id for s in seasons]))
            )
            db_episodes = episodes_result.scalars().all()
            # index: (series_id, season_number, episode_number) -> Episode
            episodes_by_triple: dict[tuple[int, int, int], Episode] = {}
            for ep in db_episodes:
                season_obj = ep.season
                if season_obj:
                    key = (season_obj.series_id, season_obj.number, ep.number)
                    episodes_by_triple[key] = ep

            # Step 7: load watch history for user
            watch_history_result = await session.execute(
                select(WatchHistory).where(
                    WatchHistory.user_id == user.id,
                    WatchHistory.episode_id.isnot(None),
                )
            )
            watch_by_episode_id: dict[int, WatchHistory] = {
                wh.episode_id: wh
                for wh in watch_history_result.scalars()
                if wh.episode_id is not None
            }
            to_insert = []
            resolved_episode_ids: set[int] = set()

            # Step 8: main loop over episodes
            for ep_data in episodes_data:
                jf_ep_id = ep_data.get("Id")
                jf_series_id = ep_data.get("SeriesId")
                season_num = ep_data.get("ParentIndexNumber")
                ep_num = ep_data.get("IndexNumber")

                if (
                    not jf_series_id
                    or not isinstance(season_num, int)
                    or not isinstance(ep_num, int)
                ):
                    logger.warning("Skip episode (incomplete payload): jellyfin_ep_id=%s", jf_ep_id)
                    continue

                if jf_series_id in unmatched_series_ids:
                    continue  # series not found — don't flood warnings

                series = series_by_jellyfin_series_id.get(jf_series_id)
                if not series:
                    if jf_series_id not in unmatched_series_ids:
                        logger.warning(
                            "Series not found for episode: jellyfin_series_id=%s", jf_series_id
                        )
                        unmatched_series_ids.add(jf_series_id)
                    continue

                episode = episodes_by_triple.get((series.id, season_num, ep_num))
                if not episode:
                    logger.warning(
                        "Episode not found in DB: series_id=%d S%02dE%02d jellyfin_ep_id=%s",
                        series.id,
                        season_num,
                        ep_num,
                        jf_ep_id,
                    )
                    continue

                # heal Episode.jellyfin_id
                if jf_ep_id and episode.jellyfin_id != jf_ep_id:
                    logger.info(
                        "Healing Episode.jellyfin_id: id=%s old=%s new=%s",
                        episode.id,
                        episode.jellyfin_id,
                        jf_ep_id,
                    )
                    episode.jellyfin_id = jf_ep_id

                # heal Season.jellyfin_id
                jf_season_id = ep_data.get("SeasonId")
                if jf_season_id and episode.season and episode.season.jellyfin_id != jf_season_id:
                    logger.info(
                        "Healing Season.jellyfin_id: id=%s old=%s new=%s",
                        episode.season.id,
                        episode.season.jellyfin_id,
                        jf_season_id,
                    )
                    episode.season.jellyfin_id = jf_season_id

                resolved_episode_ids.add(episode.id)

                user_data = ep_data.get("UserData") or {}
                played = bool(user_data.get("Played"))
                playback_ticks = user_data.get("PlaybackPositionTicks", 0) or 0
                last_played_date_str = user_data.get("LastPlayedDate")

                if played:
                    jellyfin_status = WatchStatus.WATCHED
                elif playback_ticks > 0:
                    jellyfin_status = WatchStatus.WATCHING
                else:
                    jellyfin_status = WatchStatus.PLANNED

                existing = watch_by_episode_id.get(episode.id)
                if existing:
                    if existing.is_manual:
                        total_episodes_processed += 1
                        continue
                    changed = False
                    if existing.status != jellyfin_status:
                        existing.status = jellyfin_status
                        changed = True
                    if jellyfin_status == WatchStatus.WATCHED and last_played_date_str:
                        last_played_date = parse_datetime(last_played_date_str)
                        if last_played_date and existing.watched_at != last_played_date:
                            existing.watched_at = last_played_date
                            changed = True
                    if changed:
                        user_updated += 1
                        watched_updated += 1
                elif jellyfin_status in (WatchStatus.WATCHED, WatchStatus.WATCHING):
                    watched_at = (
                        parse_datetime(last_played_date_str) if last_played_date_str else None
                    )
                    to_insert.append(
                        {
                            "user_id": user.id,
                            "media_id": series.id,
                            "episode_id": episode.id,
                            "status": jellyfin_status,
                            "is_manual": False,
                            "playback_position_ticks": playback_ticks,
                            "watched_at": watched_at,
                        }
                    )
                    user_added += 1
                    watched_added += 1

                total_episodes_processed += 1

            # Step 9: dropped-detection via resolved_episode_ids (O(n))
            for ep_id, wh in watch_by_episode_id.items():
                if (
                    ep_id not in resolved_episode_ids
                    and wh.status in (WatchStatus.PLANNED, WatchStatus.WATCHING)
                    and not wh.is_manual
                ):
                    wh.status = WatchStatus.DROPPED
                    unwatched_marked += 1
                    user_unwatched += 1
                    logger.debug("Marked dropped episode_id=%s", ep_id)

            # Step 10: bulk insert and commit
            if to_insert:
                await session.execute(insert(WatchHistory), to_insert)
            await session.commit()
            logger.info(
                "User %s: added=%d updated=%d unwatched=%d",
                user.username,
                user_added,
                user_updated,
                user_unwatched,
            )

        except Exception as e:
            await session.rollback()
            logger.error("Error syncing episodes for user %s: %s", user.username, e)
            continue

    logger.info(
        "Episodes sync completed: users=%d processed=%d added=%d updated=%d unwatched=%d",
        total_users,
        total_episodes_processed,
        watched_added,
        watched_updated,
        unwatched_marked,
    )

    return JellyfinWatchedSeriesResponse(
        total_users=total_users,
        total_episodes_processed=total_episodes_processed,
        watched_added=watched_added,
        watched_updated=watched_updated,
        unwatched_marked=unwatched_marked,
    )
