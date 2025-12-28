from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.config import logger
from app.models import Media, MediaType, Movie
from app.schemas.radarr import RadarrImportResponse
from app.services.movie_utils import (
    find_movie_by_external_ids,
    find_movie_by_radarr_id,
    parse_release_date,
)


def _update_existing_movie(
    movie: Movie,
    radarr_id: int | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    title: str,
    status: str | None = None,
) -> bool:
    """Update existing movie and return True if was changes"""
    was_updated = False

    if radarr_id and not movie.radarr_id:
        movie.radarr_id = radarr_id
        was_updated = True

    if tmdb_id and not movie.tmdb_id:
        movie.tmdb_id = tmdb_id
        was_updated = True

    if imdb_id and not movie.imdb_id:
        movie.imdb_id = imdb_id
        was_updated = True

    if release_date and movie.media.release_date is None:
        movie.media.release_date = release_date
        was_updated = True

    if status and movie.status != status:
        movie.status = status
        was_updated = True

    if was_updated:
        logger.info("Updated movie '%s' with new data", title)

    return was_updated


async def _create_new_movie(
    session: AsyncSession,
    title: str,
    radarr_id: int | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    status: str | None = None,
) -> None:
    """Create new movie"""
    media_obj = Media(
        media_type=MediaType.MOVIE,
        title=title,
        release_date=release_date,
    )
    session.add(media_obj)
    await session.flush()

    movie_obj = Movie(
        id=media_obj.id,
        radarr_id=radarr_id,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        status=status,
    )
    session.add(movie_obj)

    id_info = []
    if radarr_id:
        id_info.append(f"radarr_id={radarr_id}")
    if tmdb_id:
        id_info.append(f"tmdb={tmdb_id}")
    if imdb_id:
        id_info.append(f"imdb={imdb_id}")
    if status:
        id_info.append(f"status={status}")

    logger.info("Added new movie: %s (%s)", title, ", ".join(id_info))


async def import_radarr_movies(session: AsyncSession) -> RadarrImportResponse:
    """Imports movies from Radarr into the database with logging and aware datetime."""
    movies = await fetch_radarr_movies()
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
                if _update_existing_movie(
                    existing_movie, radarr_id, tmdb_id, imdb_id, release_date, title, status
                ):
                    updated += 1
                continue

            # 4. Если не нашли - создаем новый (только если есть идентификаторы)
            if not radarr_id and not tmdb_id and not imdb_id:
                logger.warning("Skipping movie without any IDs: %s", title)
                continue

            await _create_new_movie(
                session, title, radarr_id, tmdb_id, imdb_id, release_date, status
            )
            imported += 1

        await session.commit()

    except Exception as e:
        logger.error("Failed to commit session: %s", e)
        await session.rollback()
        raise

    logger.info("Radarr import completed: %d imported, %d updated", imported, updated)
    return RadarrImportResponse(imported_count=imported, updated_count=updated)
