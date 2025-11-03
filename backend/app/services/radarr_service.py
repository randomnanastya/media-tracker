from datetime import UTC, datetime

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.radarr_client import fetch_radarr_movies
from app.config import logger
from app.models import Media, MediaType, Movie
from app.schemas.radarr import RadarrImportResponse


async def _find_movie_by_external_ids(
    session: AsyncSession,
    tmdb_id: str | None,
    imdb_id: str | None,
) -> Movie | None:
    """Finding movie by tmdbID or ImdbID"""
    if not tmdb_id and not imdb_id:
        return None

    conditions = []
    if tmdb_id:
        conditions.append(Movie.tmdb_id == tmdb_id)
    if imdb_id:
        conditions.append(Movie.imdb_id == imdb_id)

    query = select(Movie).where(or_(*conditions))
    result = await session.execute(query)
    return result.scalar_one_or_none()


def _parse_release_date(movie_data: dict) -> datetime | None:
    """Parsing release date from movies data"""
    release_date_str = movie_data.get("inCinemas")
    if not release_date_str:
        return None

    try:
        release_date = datetime.fromisoformat(release_date_str)
        if release_date.tzinfo is None:
            release_date = release_date.replace(tzinfo=UTC)
        else:
            release_date = release_date.astimezone(UTC)
        return release_date
    except (ValueError, TypeError) as e:
        logger.error(
            "Failed to parse release date for movie '%s': %s", movie_data.get("title", "Unknown"), e
        )
        return None


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
            release_date = _parse_release_date(movie_data)
            status = movie_data.get("status")

            if radarr_id:
                exists_query = select(exists().where(Movie.radarr_id == radarr_id))
                result = await session.execute(exists_query)
                if result.scalar():
                    logger.debug("Movie with radarr_id=%s already exists: %s", radarr_id, title)
                    continue

            existing_movie = await _find_movie_by_external_ids(session, tmdb_id, imdb_id)

            if existing_movie:
                if _update_existing_movie(
                    existing_movie, radarr_id, tmdb_id, imdb_id, release_date, title, status
                ):
                    updated += 1
                continue

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
