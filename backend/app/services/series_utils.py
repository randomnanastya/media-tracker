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


def update_existing_series(
    series: Series,
    title: str | None,
    *,
    sonarr_id: int | None = None,
    jellyfin_id: str | None = None,
    tvdb_id: str | None = None,
    imdb_id: str | None = None,
    tmdb_id: str | None = None,
    release_date: datetime | None = None,
    poster_url: str | None = None,
    year: int | None = None,
    genres: list[str] | None = None,
    rating_value: float | None = None,
    rating_votes: int | None = None,
    status: str | None = None,
    source: str | None = None,
) -> bool:
    """
    Update existing series with new data from a source (Sonarr/Jellyfin).

    Args:
        series: The Series instance to update
        title: Series title
        sonarr_id: Sonarr ID to set if not already set
        jellyfin_id: Jellyfin ID to set if not already set
        tvdb_id: TVDB ID to set if not already set
        imdb_id: IMDb ID to set if not already set
        tmdb_id: TMDB ID to set if not already set
        release_date: Release date to set if not already set
        poster_url: Poster URL to set if not already set
        year: Release year to set if not already set
        genres: List of genres to set if not already set
        rating_value: Rating value to update if different
        rating_votes: Number of votes to update if different
        status: Status to update if different
        source: Source of the update (Sonarr/Jellyfin) for logging

    Returns:
        True if any changes were made, False otherwise
    """
    was_updated = False

    # Update IDs only if not already set
    if sonarr_id and series.sonarr_id is None:
        series.sonarr_id = sonarr_id
        was_updated = True

    if jellyfin_id and series.jellyfin_id is None:
        series.jellyfin_id = jellyfin_id
        was_updated = True

    if tvdb_id and series.tvdb_id is None:
        series.tvdb_id = tvdb_id
        was_updated = True

    if imdb_id and series.imdb_id is None:
        series.imdb_id = imdb_id
        was_updated = True

    if tmdb_id and series.tmdb_id is None:
        series.tmdb_id = tmdb_id
        was_updated = True

    # Update title only if different
    if title and series.media.title != title:
        series.media.title = title
        was_updated = True

    # Update optional fields only if not already set
    if poster_url and series.poster_url != poster_url:
        series.poster_url = poster_url
        was_updated = True

    if year is not None and series.year is None:
        series.year = year
        was_updated = True

    if genres is not None and series.genres is None:
        series.genres = genres
        was_updated = True

    # Update rating fields if different
    if rating_value is not None and series.rating_value != rating_value:
        series.rating_value = rating_value
        was_updated = True

    if rating_votes is not None and series.rating_votes != rating_votes:
        series.rating_votes = rating_votes
        was_updated = True

    # Update status if different
    if status is not None and series.status != status:
        series.status = status
        was_updated = True

    # Update release date only if not already set
    if release_date and series.media.release_date is None:
        series.media.release_date = release_date
        was_updated = True

    if was_updated:
        source_info = f" from {source}" if source else ""

        updated_ids = []
        if sonarr_id and series.sonarr_id == sonarr_id:
            updated_ids.append(f"sonarr_id={sonarr_id}")
        if jellyfin_id and series.jellyfin_id == jellyfin_id:
            updated_ids.append(f"jellyfin_id={jellyfin_id}")

        ids_info = f" ({', '.join(updated_ids)})" if updated_ids else ""
        logger.info("Updated series '%s'%s%s", title, ids_info, source_info)
    return was_updated
