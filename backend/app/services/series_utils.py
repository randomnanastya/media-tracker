from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Series


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
