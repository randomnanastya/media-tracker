from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import logger
from app.models import Media, MediaType, Series


async def find_series_by_external_ids(
    session: AsyncSession,
    tmdb_id: str | None,
    imdb_id: str | None,
    tvdb_id: str | None,
) -> Series | None:
    """Finding movie by tmdbID or ImdbID with media loaded"""
    conditions = []

    if tmdb_id:
        conditions.append(Series.tmdb_id == tmdb_id)
    if imdb_id:
        conditions.append(Series.imdb_id == imdb_id)
    if tvdb_id:
        conditions.append(Series.tvdb_id == tvdb_id)

    if not conditions:
        return None

    result = await session.execute(
        select(Series).options(selectinload(Series.media)).where(or_(*conditions))
    )
    return result.scalar_one_or_none()


async def create_new_series(
    session: AsyncSession,
    *,
    title: str,
    sonarr_id: int | None = None,
    jellyfin_id: str | None = None,
    tvdb_id: str | None = None,
    imdb_id: str | None = None,
    tmdb_id: str | None = None,
    release_date: datetime | None = None,
    status: str | None = None,
    year: int | None = None,
    poster_url: str | None = None,
    genres: list[str] | None = None,
    rating_value: float | None = None,
    rating_votes: int | None = None,
    source: str | None = None,
) -> Series:
    """
    Create new series with Media.

    Args:
        session: Database session
        title: Series title
        sonarr_id: Sonarr ID (from Sonarr)
        jellyfin_id: Jellyfin ID (from Jellyfin)
        tvdb_id: TVDB ID
        imdb_id: IMDb ID
        tmdb_id: TMDB ID
        release_date: Release date
        status: Series status
        year: Release year
        poster_url: Poster URL
        genres: List of genres
        rating_value: Rating value
        rating_votes: Number of votes
        source: Source of the data (Sonarr/Jellyfin)

    Returns:
        Created Series instance
    """
    media = Media(
        media_type=MediaType.SERIES,
        title=title,
        release_date=release_date,
    )
    session.add(media)
    await session.flush()

    series = Series(
        id=media.id,
        sonarr_id=sonarr_id,
        jellyfin_id=jellyfin_id,
        tvdb_id=tvdb_id,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        poster_url=poster_url,
        year=year,
        genres=genres,
        rating_value=rating_value,
        rating_votes=rating_votes,
        status=status,
    )
    session.add(series)
    media.series = series
    await session.flush()

    ids = []
    if sonarr_id:
        ids.append(f"sonarr_id={sonarr_id}")
    if jellyfin_id:
        ids.append(f"jellyfin_id={jellyfin_id}")
    if tvdb_id:
        ids.append(f"tvdb={tvdb_id}")
    if imdb_id:
        ids.append(f"imdb={imdb_id}")
    if tmdb_id:
        ids.append(f"tmdb={tmdb_id}")

    source_info = f" from {source}" if source else ""
    ids_info = ", ".join(ids) if ids else "no IDs"
    logger.info("Created new series%s: %s (%s)", source_info, title, ids_info)

    return series
