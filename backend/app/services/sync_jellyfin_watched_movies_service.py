from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_movies_for_user_all
from app.config import logger
from app.models import Movie, ServiceType, User, WatchHistory
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

    logger.info(f"Starting watched movies sync for {total_users} users")

    for user in users:
        user_added = user_updated = user_unwatched = 0
        if not user.jellyfin_user_id:
            continue

        logger.info(f"Processing movies for user {user.username}")
        try:
            # 2. Get all movies by user from Jellyfin (with pagination into func)
            movies_data = await fetch_jellyfin_movies_for_user_all(
                url, api_key, user.jellyfin_user_id
            )

            if not movies_data:
                logger.info(f"No movies found for user {user.username}")
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
                        f"Movie not found in database: {movie_data.get('Name')} (Jellyfin ID: {jellyfin_id})"
                    )
                    continue

                # Data about watching
                user_data = movie_data.get("UserData", {})
                played = user_data.get("Played", False)
                last_played_date_str = user_data.get("LastPlayedDate")

                # found existing row into saved dict
                existing_watch = current_watches.get(movie.id)

                # Situation 1: movie was watched
                if played and last_played_date_str:
                    last_played_date = parse_datetime(last_played_date_str)
                    if not last_played_date:
                        logger.debug(f"Could not parse date for: {movie_data.get('Name')}")
                        continue

                    if existing_watch:
                        # updating if need
                        if (
                            not existing_watch.is_watched
                            or last_played_date != existing_watch.watched_at
                        ):
                            existing_watch.is_watched = True
                            existing_watch.watched_at = last_played_date
                            watched_updated += 1
                            user_updated += 1
                            logger.debug(f"Updated: {movie.id}")
                    else:
                        # creating new
                        watch_history = WatchHistory(
                            user_id=user.id,
                            media_id=movie.id,
                            episode_id=None,
                            is_watched=True,
                            watched_at=last_played_date,
                        )
                        session.add(watch_history)
                        watched_added += 1
                        user_added += 1
                        logger.debug(f"Added: {movie.id}")

                # Situation 2: movie watched false
                elif existing_watch and existing_watch.is_watched:
                    existing_watch.is_watched = False
                    unwatched_marked += 1
                    user_unwatched += 1
                    logger.debug(f"Marked unwatched: {movie.id}")

            # 5. Save changes
            await session.commit()
            logger.info(
                f"User {user.username}: "
                f"movies={len(movies_data)}, "
                f"added={user_added}, "
                f"updated={user_updated}, "
                f"unwatched={user_unwatched}"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error for user {user.username}: {e}")
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
