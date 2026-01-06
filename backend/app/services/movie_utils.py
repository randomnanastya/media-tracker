from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import logger
from app.models import Media, MediaType, Movie


async def find_movie_by_external_ids(
    session: AsyncSession,
    tmdb_id: str | None,
    imdb_id: str | None,
) -> Movie | None:
    """Finding movie by tmdbID or ImdbID with media loaded"""
    if not tmdb_id and not imdb_id:
        return None

    conditions = []
    if tmdb_id:
        conditions.append(Movie.tmdb_id == tmdb_id)
    if imdb_id:
        conditions.append(Movie.imdb_id == imdb_id)

    query = select(Movie).where(or_(*conditions)).options(selectinload(Movie.media))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def find_movie_by_radarr_id(session: AsyncSession, radarr_id: int) -> Movie | None:
    """Finding movie by radarr_id with media loaded"""
    query = select(Movie).where(Movie.radarr_id == radarr_id).options(selectinload(Movie.media))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def find_movie_by_jellyfin_id(session: AsyncSession, jellyfin_id: str) -> Movie | None:
    """Finding movie by jellyfin_id with media loaded"""
    query = select(Movie).where(Movie.jellyfin_id == jellyfin_id).options(selectinload(Movie.media))
    result = await session.execute(query)
    return result.scalar_one_or_none()


def parse_release_date(
    release_date_str: str | None, movie_title: str = "Unknown"
) -> datetime | None:
    """Parsing release date from string"""
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
        logger.error("Failed to parse release date for movie '%s': %s", movie_title, e)
        return None


async def create_new_movie(
    session: AsyncSession,
    title: str,
    radarr_id: int | None,
    jellyfin_id: str | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    status: str | None = None,
    source: str | None = None,
) -> None:
    """Create a new movie with associated Media entry."""
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
        jellyfin_id=jellyfin_id,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        status=status,
    )
    session.add(movie_obj)

    id_info = []
    if radarr_id:
        id_info.append(f"radarr_id={radarr_id}")
    if jellyfin_id:
        id_info.append(f"jellyfin_id={jellyfin_id}")
    if tmdb_id:
        id_info.append(f"tmdb={tmdb_id}")
    if imdb_id:
        id_info.append(f"imdb={imdb_id}")
    if status:
        id_info.append(f"status={status}")

    logger.info("Added new movie from %s: %s (%s)", source, title, ", ".join(id_info))


def update_existing_movie(
    movie: Movie,
    *,
    radarr_id: int | None,
    jellyfin_id: str | None,
    tmdb_id: str | None,
    imdb_id: str | None,
    release_date: datetime | None,
    title: str,
    status: str | None = None,
    source: str | None = None,
) -> bool:
    """
    Update existing movie with new data from a source (Radarr/Jellyfin).

    Args:
        movie: The Movie instance to update
        radarr_id: Radarr ID to set if not already set
        jellyfin_id: Jellyfin ID to set if not already set
        tmdb_id: TMDB ID to set if not already set
        imdb_id: IMDb ID to set if not already set
        release_date: Release date to set if not already set
        title: Movie title for logging
        status: Status to update if different
        source: Source of the update (Radarr/Jellyfin) for logging

    Returns:
        True if any changes were made, False otherwise
    """
    was_updated = False

    if radarr_id and not movie.radarr_id:
        movie.radarr_id = radarr_id
        was_updated = True

    if jellyfin_id and not movie.jellyfin_id:
        movie.jellyfin_id = jellyfin_id
        was_updated = True

    if tmdb_id and not movie.tmdb_id:
        movie.tmdb_id = tmdb_id
        was_updated = True

    if imdb_id and not movie.imdb_id:
        movie.imdb_id = imdb_id
        was_updated = True

    if release_date and movie.media and movie.media.release_date is None:
        movie.media.release_date = release_date
        was_updated = True

    if status and movie.status != status:
        movie.status = status
        was_updated = True

    if was_updated:
        source_info = f" from {source}" if source else ""
        logger.info("Updated movie '%s' with new data %s", title, source_info)

    return was_updated
