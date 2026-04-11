from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.jellyfin_client import fetch_jellyfin_episodes_for_user_all
from app.config import logger
from app.models import Episode, Season, ServiceType, User, WatchHistory, WatchStatus
from app.schemas.jellyfin import JellyfinWatchedSeriesResponse
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
            # 2. Get all episodes by user from Jellyfin (with pagination into func)
            episodes_data = await fetch_jellyfin_episodes_for_user_all(
                url, api_key, user.jellyfin_user_id
            )

            if not episodes_data:
                logger.info("No episodes found for user %s", user.username)
                continue

            # --- episodes from DB ---
            jellyfin_ids = [ep["Id"] for ep in episodes_data if ep.get("Id")]

            episodes_result = await session.execute(
                select(Episode)
                .options(selectinload(Episode.season).selectinload(Season.series))
                .where(Episode.jellyfin_id.in_(jellyfin_ids))
            )
            episodes_by_jellyfin_id = {e.jellyfin_id: e for e in episodes_result.scalars()}

            watch_history_result = await session.execute(
                select(WatchHistory).where(
                    WatchHistory.user_id == user.id,
                    WatchHistory.episode_id.isnot(None),
                )
            )
            watch_by_episode_id = {wh.episode_id: wh for wh in watch_history_result.scalars()}
            to_insert = []

            for ep_data in episodes_data:
                jellyfin_id = ep_data.get("Id")
                episode = episodes_by_jellyfin_id.get(jellyfin_id)
                if not episode:
                    continue

                if not episode.season or not episode.season.series:
                    logger.error(
                        "Broken episode relations: episode_id=%s jellyfin_id=%s",
                        episode.id,
                        episode.jellyfin_id,
                    )
                    continue

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
                    media_id = episode.season.series.id
                    watched_at = (
                        parse_datetime(last_played_date_str) if last_played_date_str else None
                    )
                    to_insert.append(
                        {
                            "user_id": user.id,
                            "media_id": media_id,
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

            logger.info(
                "User %s: added=%d updated=%d unwatched=%d",
                user.username,
                user_added,
                user_updated,
                user_unwatched,
            )

            # Dropped detection: episodes that disappeared from Jellyfin
            jellyfin_episode_ids = {ep["Id"] for ep in episodes_data if ep.get("Id")}
            for ep_id, wh in watch_by_episode_id.items():
                ep = next((e for e in episodes_by_jellyfin_id.values() if e.id == ep_id), None)
                if (
                    ep
                    and ep.jellyfin_id not in jellyfin_episode_ids
                    and wh.status in (WatchStatus.PLANNED, WatchStatus.WATCHING)
                    and not wh.is_manual
                ):
                    wh.status = WatchStatus.DROPPED

            if to_insert:
                await session.execute(insert(WatchHistory), to_insert)

            await session.commit()

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
