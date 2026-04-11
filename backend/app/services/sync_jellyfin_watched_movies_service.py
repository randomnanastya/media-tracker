from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_movies_for_user_all
from app.config import logger
from app.models import Movie, ServiceType, User, WatchHistory, WatchStatus
from app.schemas.jellyfin import JellyfinWatchedMoviesResponse
from app.services.service_config_repository import get_decrypted_config
from app.utils.datetime import parse_datetime


async def sync_jellyfin_watched_movies(session: AsyncSession) -> JellyfinWatchedMoviesResponse:
    """
    Sync watched movies from Jellyfin for all users.
    """
    config = await get_decrypted_config(session, ServiceType.JELLYFIN)
    if config is None:
        logger.info("Jellyfin is not configured, skipping sync")
        return JellyfinWatchedMoviesResponse(
            total_users=0,
            total_movies_processed=0,
            watched_added=0,
            watched_updated=0,
            unwatched_marked=0,
        )
    url, api_key = config

    # 1. Get all users with jellyfin_user_id
    users_result = await session.execute(select(User).where(User.jellyfin_user_id.isnot(None)))
    users = users_result.scalars().all()

    total_users = len(users)
    total_movies_processed = 0
    watched_added = 0
    watched_updated = 0
    unwatched_marked = 0

    logger.info("Starting watched movies sync for %s users", total_users)

    for user in users:
        user_added = user_updated = user_unwatched = 0
        if not user.jellyfin_user_id:
            continue

        logger.info("Processing movies for user %s", user.username)
        try:
            # 2. Get all movies by user from Jellyfin (with pagination into func)
            movies_data = await fetch_jellyfin_movies_for_user_all(
                url, api_key, user.jellyfin_user_id
            )

            if not movies_data:
                logger.info("No movies found for user %s", user.username)
                continue

            # 3. Create data for fast finding

            # 3a. Get all rows from watch_history by user (one request)
            current_watches_result = await session.execute(
                select(WatchHistory).where(
                    WatchHistory.user_id == user.id, WatchHistory.episode_id.is_(None)
                )
            )
            current_watches: dict[int, WatchHistory] = {
                wh.media_id: wh for wh in current_watches_result.scalars()
            }

            # 3b. Save all jellyfin_id and external_id for package fining movies
            jellyfin_ids = []
            tmdb_ids = []
            imdb_ids = []

            for movie_data in movies_data:
                jellyfin_id = str(movie_data.get("Id")) if movie_data.get("Id") else None
                if jellyfin_id:
                    jellyfin_ids.append(jellyfin_id)

                provider_ids = movie_data.get("ProviderIds", {})
                tmdb_id = str(provider_ids.get("Tmdb")) if provider_ids.get("Tmdb") else None
                if tmdb_id:
                    tmdb_ids.append(tmdb_id)

                imdb_id = provider_ids.get("Imdb")
                if imdb_id:
                    imdb_ids.append(imdb_id)

            # 3c. Package finding movies
            movies_by_jellyfin_id = {}
            movies_by_tmdb_id = {}
            movies_by_imdb_id = {}

            if jellyfin_ids:
                movies_result = await session.execute(
                    select(Movie).where(Movie.jellyfin_id.in_(jellyfin_ids))
                )
                for db_movie in movies_result.scalars():
                    if db_movie.jellyfin_id:
                        movies_by_jellyfin_id[db_movie.jellyfin_id] = db_movie

            if tmdb_ids:
                movies_result = await session.execute(
                    select(Movie).where(Movie.tmdb_id.in_(tmdb_ids))
                )
                for db_movie in movies_result.scalars():
                    if db_movie.tmdb_id:
                        movies_by_tmdb_id[db_movie.tmdb_id] = db_movie

            if imdb_ids:
                movies_result = await session.execute(
                    select(Movie).where(Movie.imdb_id.in_(imdb_ids))
                )
                for db_movie in movies_result.scalars():
                    if db_movie.imdb_id:
                        movies_by_imdb_id[db_movie.imdb_id] = db_movie

            # 4. Processed movies
            for movie_data in movies_data:
                total_movies_processed += 1

                # Find movie into saved data
                movie: Movie | None = None
                jellyfin_id = str(movie_data.get("Id")) if movie_data.get("Id") else None

                if jellyfin_id and jellyfin_id in movies_by_jellyfin_id:
                    movie = movies_by_jellyfin_id[jellyfin_id]
                else:
                    provider_ids = movie_data.get("ProviderIds", {})
                    tmdb_id = str(provider_ids.get("Tmdb")) if provider_ids.get("Tmdb") else None
                    imdb_id = provider_ids.get("Imdb")

                    if tmdb_id and tmdb_id in movies_by_tmdb_id:
                        movie = movies_by_tmdb_id[tmdb_id]
                    elif imdb_id and imdb_id in movies_by_imdb_id:
                        movie = movies_by_imdb_id[imdb_id]

                if not movie:
                    logger.debug(
                        "Movie not found in database: %s (Jellyfin ID: %s)",
                        movie_data.get("Name"),
                        jellyfin_id,
                    )
                    continue

                # Data about watching
                user_data = movie_data.get("UserData", {})
                played = user_data.get("Played", False)
                playback_ticks = user_data.get("PlaybackPositionTicks", 0) or 0
                last_played_date_str = user_data.get("LastPlayedDate")

                if played:
                    jellyfin_status = WatchStatus.WATCHED
                elif playback_ticks > 0:
                    jellyfin_status = WatchStatus.WATCHING
                else:
                    jellyfin_status = WatchStatus.PLANNED

                existing_watch = current_watches.get(movie.id)

                if existing_watch:
                    if existing_watch.is_manual:
                        continue  # не трогаем ручные записи
                    changed = False
                    if existing_watch.status != jellyfin_status:
                        existing_watch.status = jellyfin_status
                        changed = True
                    if existing_watch.playback_position_ticks != playback_ticks:
                        existing_watch.playback_position_ticks = playback_ticks
                        changed = True
                    if jellyfin_status == WatchStatus.WATCHED and last_played_date_str:
                        last_played_date = parse_datetime(last_played_date_str)
                        if last_played_date and existing_watch.watched_at != last_played_date:
                            existing_watch.watched_at = last_played_date
                            changed = True
                    if changed:
                        watched_updated += 1
                        user_updated += 1
                        logger.debug("Updated: %s", movie.id)
                else:
                    watched_at = (
                        parse_datetime(last_played_date_str) if last_played_date_str else None
                    )
                    watch_history = WatchHistory(
                        user_id=user.id,
                        media_id=movie.id,
                        episode_id=None,
                        status=jellyfin_status,
                        is_manual=False,
                        playback_position_ticks=playback_ticks,
                        watched_at=watched_at,
                    )
                    session.add(watch_history)
                    watched_added += 1
                    user_added += 1
                    logger.debug("Added: %s", movie.id)

            # 4b. Dropped detection: фильмы, исчезнувшие из Jellyfin
            jellyfin_media_ids = set()
            for movie_data in movies_data:
                jellyfin_id = str(movie_data.get("Id")) if movie_data.get("Id") else None
                if jellyfin_id and jellyfin_id in movies_by_jellyfin_id:
                    jellyfin_media_ids.add(movies_by_jellyfin_id[jellyfin_id].id)
                else:
                    provider_ids = movie_data.get("ProviderIds", {})
                    tmdb_id = str(provider_ids.get("Tmdb")) if provider_ids.get("Tmdb") else None
                    imdb_id = provider_ids.get("Imdb")
                    if tmdb_id and tmdb_id in movies_by_tmdb_id:
                        jellyfin_media_ids.add(movies_by_tmdb_id[tmdb_id].id)
                    elif imdb_id and imdb_id in movies_by_imdb_id:
                        jellyfin_media_ids.add(movies_by_imdb_id[imdb_id].id)

            for media_id, wh in current_watches.items():
                if (
                    media_id not in jellyfin_media_ids
                    and wh.status != WatchStatus.WATCHED
                    and not wh.is_manual
                ):
                    wh.status = WatchStatus.DROPPED
                    unwatched_marked += 1
                    user_unwatched += 1
                    logger.debug("Marked dropped: %s", media_id)

            # 5. Save changes
            await session.commit()
            logger.info(
                "User %s: movies=%d, added=%d, updated=%d, unwatched=%d",
                user.username,
                len(movies_data),
                user_added,
                user_updated,
                user_unwatched,
            )

        except Exception as e:
            await session.rollback()
            logger.error("Error for user %s: %s", user.username, e)
            continue

    logger.info(
        f"Sync completed: "
        f"users={total_users}, "
        f"processed={total_movies_processed}, "
        f"added={watched_added}, "
        f"updated={watched_updated}, "
        f"unwatched={unwatched_marked}"
    )

    return JellyfinWatchedMoviesResponse(
        total_users=total_users,
        total_movies_processed=total_movies_processed,
        watched_added=watched_added,
        watched_updated=watched_updated,
        unwatched_marked=unwatched_marked,
    )
