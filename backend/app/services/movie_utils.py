from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import logger
from app.models import Movie


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
