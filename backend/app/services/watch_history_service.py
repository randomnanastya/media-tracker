from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Episode, Media, MediaType, Season
from app.models.user import User, WatchHistory, WatchStatus
from app.schemas.error_codes import WatchErrorCode
from app.schemas.watch_history import BulkWatchStatusResponse, ManualWatchStatus


async def _get_user_by_jellyfin_id(session: AsyncSession, jellyfin_user_id: str) -> User:
    result = await session.execute(select(User).where(User.jellyfin_user_id == jellyfin_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.USER_NOT_FOUND},
        )
    return user


async def _upsert_watch_history(
    session: AsyncSession,
    user_id: int,
    media_id: int,
    episode_id: int | None,
    status: ManualWatchStatus,
) -> tuple[WatchHistory, bool]:
    result = await session.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user_id,
            WatchHistory.media_id == media_id,
            WatchHistory.episode_id == episode_id,
        )
    )
    wh = result.scalar_one_or_none()
    created = wh is None

    if wh is None:
        wh = WatchHistory(
            user_id=user_id,
            media_id=media_id,
            episode_id=episode_id,
        )
        session.add(wh)

    wh.is_manual = True
    wh.playback_position_ticks = None
    if status == ManualWatchStatus.WATCHED:
        wh.status = WatchStatus.WATCHED
        wh.watched_at = datetime.now(UTC)
    elif status == ManualWatchStatus.WATCHING:
        wh.status = WatchStatus.WATCHING
        wh.watched_at = None
    elif status == ManualWatchStatus.DROPPED:
        wh.status = WatchStatus.DROPPED
        wh.watched_at = None
    else:
        wh.status = WatchStatus.PLANNED
        wh.watched_at = None

    return wh, created


async def _bulk_upsert(
    session: AsyncSession,
    user_id: int,
    media_id: int,
    episode_ids: list[int],
    status: ManualWatchStatus,
) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for episode_id in episode_ids:
        _, created = await _upsert_watch_history(session, user_id, media_id, episode_id, status)
        if created:
            inserted += 1
        else:
            updated += 1
    return inserted, updated


async def set_movie_watch_status(
    session: AsyncSession,
    jellyfin_user_id: str,
    media_id: int,
    status: ManualWatchStatus,
) -> WatchHistory:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    media_result = await session.execute(
        select(Media).where(Media.id == media_id, Media.media_type == MediaType.MOVIE)
    )
    if media_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.MEDIA_NOT_FOUND},
        )

    wh, _ = await _upsert_watch_history(session, user.id, media_id, None, status)
    return wh


async def clear_movie_manual_flag(
    session: AsyncSession,
    jellyfin_user_id: str,
    media_id: int,
) -> None:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    media_result = await session.execute(
        select(Media).where(Media.id == media_id, Media.media_type == MediaType.MOVIE)
    )
    if media_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.MEDIA_NOT_FOUND},
        )

    result = await session.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user.id,
            WatchHistory.media_id == media_id,
            WatchHistory.episode_id.is_(None),
        )
    )
    wh = result.scalar_one_or_none()
    if wh is not None:
        wh.is_manual = False


async def set_episode_watch_status(
    session: AsyncSession,
    jellyfin_user_id: str,
    episode_id: int,
    status: ManualWatchStatus,
) -> WatchHistory:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    ep_result = await session.execute(
        select(Episode, Season.series_id)
        .join(Season, Season.id == Episode.season_id)
        .where(Episode.id == episode_id)
    )
    row = ep_result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.EPISODE_NOT_FOUND},
        )
    _, series_id = row
    media_id: int = series_id

    wh, _ = await _upsert_watch_history(session, user.id, media_id, episode_id, status)
    return wh


async def clear_episode_manual_flag(
    session: AsyncSession,
    jellyfin_user_id: str,
    episode_id: int,
) -> None:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    ep_check = await session.execute(select(Episode).where(Episode.id == episode_id))
    if ep_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.EPISODE_NOT_FOUND},
        )

    result = await session.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user.id,
            WatchHistory.episode_id == episode_id,
        )
    )
    wh = result.scalar_one_or_none()
    if wh is not None:
        wh.is_manual = False


async def set_season_watch_status(
    session: AsyncSession,
    jellyfin_user_id: str,
    season_id: int,
    status: ManualWatchStatus,
) -> BulkWatchStatusResponse:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    season_result = await session.execute(select(Season).where(Season.id == season_id))
    season = season_result.scalar_one_or_none()
    if season is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.SEASON_NOT_FOUND},
        )

    ep_ids_result = await session.execute(select(Episode.id).where(Episode.season_id == season_id))
    episode_ids = list(ep_ids_result.scalars().all())

    media_id: int = season.series_id
    inserted, updated = await _bulk_upsert(session, user.id, media_id, episode_ids, status)

    return BulkWatchStatusResponse(
        affected=len(episode_ids),
        inserted=inserted,
        updated=updated,
    )


async def clear_season_manual_flag(
    session: AsyncSession,
    jellyfin_user_id: str,
    season_id: int,
) -> BulkWatchStatusResponse:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    season_result = await session.execute(select(Season).where(Season.id == season_id))
    if season_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.SEASON_NOT_FOUND},
        )

    episode_ids_subq = select(Episode.id).where(Episode.season_id == season_id)
    wh_result = await session.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user.id,
            WatchHistory.episode_id.in_(episode_ids_subq),
        )
    )
    records = list(wh_result.scalars().all())
    for wh in records:
        wh.is_manual = False

    return BulkWatchStatusResponse(
        affected=len(records),
        inserted=0,
        updated=len(records),
    )


async def set_series_watch_status(
    session: AsyncSession,
    jellyfin_user_id: str,
    series_media_id: int,
    status: ManualWatchStatus,
) -> BulkWatchStatusResponse:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    media_result = await session.execute(
        select(Media).where(Media.id == series_media_id, Media.media_type == MediaType.SERIES)
    )
    if media_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.SERIES_NOT_FOUND},
        )

    ep_ids_result = await session.execute(
        select(Episode.id).join(Season).where(Season.series_id == series_media_id)
    )
    episode_ids = list(ep_ids_result.scalars().all())

    inserted, updated = await _bulk_upsert(session, user.id, series_media_id, episode_ids, status)

    return BulkWatchStatusResponse(
        affected=len(episode_ids),
        inserted=inserted,
        updated=updated,
    )


async def clear_series_manual_flag(
    session: AsyncSession,
    jellyfin_user_id: str,
    series_media_id: int,
) -> BulkWatchStatusResponse:
    user = await _get_user_by_jellyfin_id(session, jellyfin_user_id)

    media_result = await session.execute(
        select(Media).where(Media.id == series_media_id, Media.media_type == MediaType.SERIES)
    )
    if media_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail={"code": WatchErrorCode.SERIES_NOT_FOUND},
        )

    episode_ids_subq = select(Episode.id).join(Season).where(Season.series_id == series_media_id)
    wh_result = await session.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user.id,
            WatchHistory.episode_id.in_(episode_ids_subq),
        )
    )
    records = list(wh_result.scalars().all())
    for wh in records:
        wh.is_manual = False

    return BulkWatchStatusResponse(
        affected=len(records),
        inserted=0,
        updated=len(records),
    )
