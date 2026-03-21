from sqlalchemy.ext.asyncio import AsyncSession

from app.client.jellyfin_client import fetch_jellyfin_movies
from app.config import logger
from app.models import ServiceType
from app.schemas.jellyfin import JellyfinImportMoviesResponse
from app.services.movie_utils import (
    create_new_movie,
    find_movie_by_external_ids,
    find_movie_by_jellyfin_id,
    parse_release_date,
    update_existing_movie,
)
from app.services.service_config_repository import get_decrypted_config


async def import_jellyfin_movies(session: AsyncSession) -> JellyfinImportMoviesResponse:
    """Import movies from Jellyfin into the database."""
    config = await get_decrypted_config(session, ServiceType.JELLYFIN)
    if config is None:
        logger.info("Jellyfin is not configured, skipping import")
        return JellyfinImportMoviesResponse(imported_count=0, updated_count=0)
    url, api_key = config
    movies = await fetch_jellyfin_movies(url, api_key)
    imported = 0
    updated = 0

    try:
        for movie_data in movies:
            jellyfin_id_raw = movie_data.get("Id")
            jellyfin_id = str(jellyfin_id_raw) if jellyfin_id_raw is not None else None
            title = movie_data.get("Name", "Unknown Title")
            release_date = parse_release_date(movie_data.get("PremiereDate"), title)
            tmdb_id_raw = movie_data.get("ProviderIds", {}).get("Tmdb")
            tmdb_id = str(tmdb_id_raw) if tmdb_id_raw is not None else None
            imdb_id_raw = movie_data.get("ProviderIds", {}).get("Imdb")
            imdb_id = str(imdb_id_raw) if imdb_id_raw is not None else None

            # Skip if no identifiers are provided
            if not jellyfin_id and not tmdb_id and not imdb_id:
                logger.warning("Skipping movie without any IDs: %s", title)
                continue

            existing_movie = None

            # 1. First, search by jellyfin_id (if available)
            if jellyfin_id:
                existing_movie = await find_movie_by_jellyfin_id(session, jellyfin_id)

            # 2. If not found by jellyfin_id, search by external IDs
            if not existing_movie:
                existing_movie = await find_movie_by_external_ids(session, tmdb_id, imdb_id)

            # 3. Update existing movie
            if existing_movie:
                if update_existing_movie(
                    movie=existing_movie,
                    radarr_id=None,
                    jellyfin_id=jellyfin_id,
                    tmdb_id=tmdb_id,
                    imdb_id=imdb_id,
                    release_date=release_date,
                    title=title,
                    status=None,
                    source="Jellyfin",
                ):
                    updated += 1
            else:
                # 4. Create new movie
                await create_new_movie(
                    session=session,
                    title=title,
                    radarr_id=None,
                    jellyfin_id=jellyfin_id,
                    tmdb_id=tmdb_id,
                    imdb_id=imdb_id,
                    release_date=release_date,
                    status=None,
                    source="Jellyfin",
                )
                imported += 1

        await session.commit()

    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Jellyfin import completed: %d imported, %d updated", imported, updated)
    return JellyfinImportMoviesResponse(imported_count=imported, updated_count=updated)
