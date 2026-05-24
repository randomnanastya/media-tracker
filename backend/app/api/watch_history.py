from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.watch_history import (
    BulkWatchStatusRequest,
    BulkWatchStatusResponse,
    WatchHistoryItem,
    WatchStatusUpdateRequest,
    WatchStatusUpdateResponse,
)
from app.services import watch_history_service

router = APIRouter(prefix="/api/v1/watch", tags=["watch-history"])


@router.put("/movies/{media_id}", response_model=WatchStatusUpdateResponse)
async def set_movie_watch_status(
    media_id: int,
    body: WatchStatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> WatchStatusUpdateResponse:
    wh = await watch_history_service.set_movie_watch_status(
        session, body.jellyfin_user_id, media_id, body.status
    )
    item = WatchHistoryItem(
        media_id=wh.media_id,
        episode_id=wh.episode_id,
        status=wh.status.value,
        is_manual=wh.is_manual,
        watched_at=wh.watched_at,
    )
    await session.commit()
    return WatchStatusUpdateResponse(item=item)


@router.delete("/movies/{media_id}/manual", status_code=204)
async def clear_movie_manual_flag(
    media_id: int,
    jellyfin_user_id: str = Query(..., description="Jellyfin user UUID"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await watch_history_service.clear_movie_manual_flag(session, jellyfin_user_id, media_id)
    await session.commit()
    return Response(status_code=204)


@router.put("/episodes/{episode_id}", response_model=WatchStatusUpdateResponse)
async def set_episode_watch_status(
    episode_id: int,
    body: WatchStatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> WatchStatusUpdateResponse:
    wh = await watch_history_service.set_episode_watch_status(
        session, body.jellyfin_user_id, episode_id, body.status
    )
    item = WatchHistoryItem(
        media_id=wh.media_id,
        episode_id=wh.episode_id,
        status=wh.status.value,
        is_manual=wh.is_manual,
        watched_at=wh.watched_at,
    )
    await session.commit()
    return WatchStatusUpdateResponse(item=item)


@router.delete("/episodes/{episode_id}/manual", status_code=204)
async def clear_episode_manual_flag(
    episode_id: int,
    jellyfin_user_id: str = Query(..., description="Jellyfin user UUID"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await watch_history_service.clear_episode_manual_flag(session, jellyfin_user_id, episode_id)
    await session.commit()
    return Response(status_code=204)


@router.put("/seasons/{season_id}", response_model=BulkWatchStatusResponse)
async def set_season_watch_status(
    season_id: int,
    body: BulkWatchStatusRequest,
    session: AsyncSession = Depends(get_session),
) -> BulkWatchStatusResponse:
    result = await watch_history_service.set_season_watch_status(
        session, body.jellyfin_user_id, season_id, body.status
    )
    await session.commit()
    return result


@router.delete("/seasons/{season_id}/manual", response_model=BulkWatchStatusResponse)
async def clear_season_manual_flag(
    season_id: int,
    jellyfin_user_id: str = Query(..., description="Jellyfin user UUID"),
    session: AsyncSession = Depends(get_session),
) -> BulkWatchStatusResponse:
    result = await watch_history_service.clear_season_manual_flag(
        session, jellyfin_user_id, season_id
    )
    await session.commit()
    return result


@router.put("/series/{media_id}", response_model=BulkWatchStatusResponse)
async def set_series_watch_status(
    media_id: int,
    body: BulkWatchStatusRequest,
    session: AsyncSession = Depends(get_session),
) -> BulkWatchStatusResponse:
    result = await watch_history_service.set_series_watch_status(
        session, body.jellyfin_user_id, media_id, body.status
    )
    await session.commit()
    return result


@router.delete("/series/{media_id}/manual", response_model=BulkWatchStatusResponse)
async def clear_series_manual_flag(
    media_id: int,
    jellyfin_user_id: str = Query(..., description="Jellyfin user UUID"),
    session: AsyncSession = Depends(get_session),
) -> BulkWatchStatusResponse:
    result = await watch_history_service.clear_series_manual_flag(
        session, jellyfin_user_id, media_id
    )
    await session.commit()
    return result
