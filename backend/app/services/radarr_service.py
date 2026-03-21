from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.config import logger
from app.models import ServiceType
from app.schemas.radarr import RadarrImportResponse
from app.services.movie_utils import (
    create_new_movie,
    find_movie_by_external_ids,
    find_movie_by_radarr_id,
    parse_release_date,
    update_existing_movie,
)
from app.services.service_config_repository import get_decrypted_config


async def import_radarr_movies(session: AsyncSession) -> RadarrImportResponse:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    config = await get_decrypted_config(session, ServiceType.RADARR)
    if config is None:
        logger.info("Radarr is not configured, skipping import")
        return RadarrImportResponse(imported_count=0, updated_count=0)
    url, api_key = config
    movies = await fetch_radarr_movies(url, api_key)
    imported = 0
    updated = 0

    try:
        for movie_data in movies:
            radarr_id = movie_data.get("id")
            title = movie_data.get("title", "Unknown Title")
            tmdb_id = str(movie_data.get("tmdbId")) if movie_data.get("tmdbId") else None
            imdb_id = movie_data.get("imdbId")
            release_date = parse_release_date(movie_data.get("inCinemas"), title)
            status = movie_data.get("status")

            existing_movie = None

            # 1. Сначала ищем по radarr_id (если он есть)
            if radarr_id:
                existing_movie = await find_movie_by_radarr_id(session, radarr_id)
                if existing_movie:
                    logger.debug("Found existing movie by radarr_id=%s: %s", radarr_id, title)

            # 2. Если не нашли по radarr_id, ищем по внешним ID
            if not existing_movie:
                existing_movie = await find_movie_by_external_ids(session, tmdb_id, imdb_id)

            # 3. Если нашли существующий фильм - обновляем
            if existing_movie:
                if update_existing_movie(
                    movie=existing_movie,
                    radarr_id=radarr_id,
                    jellyfin_id=None,
                    tmdb_id=tmdb_id,
                    imdb_id=imdb_id,
                    release_date=release_date,
                    title=title,
                    status=status,
                    source="Radarr",
                ):
                    updated += 1
                continue

            # 4. Если не нашли - создаем новый (только если есть идентификаторы)
            if not radarr_id and not tmdb_id and not imdb_id:
                logger.warning("Skipping movie without any IDs: %s", title)
                continue

            await create_new_movie(
                session=session,
                title=title,
                radarr_id=radarr_id,
                jellyfin_id=None,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                release_date=release_date,
                status=status,
                source="Radarr",
            )

            imported += 1

        await session.commit()

    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Radarr import completed: %d imported, %d updated", imported, updated)
    return RadarrImportResponse(imported_count=imported, updated_count=updated)
