from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.jellyfin import (
    JellyfinImportMoviesResponse,
    JellyfinImportSeriesResponse,
    JellyfinUsersResponse,
    JellyfinWatchedMoviesResponse,
    JellyfinWatchedSeriesResponse,
)
from app.services.import_jellyfin_movies_service import import_jellyfin_movies
from app.services.import_jellyfin_series_service import import_jellyfin_series
from app.services.jellyfin_users_service import import_jellyfin_users
from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies
from app.services.sync_jellyfin_watched_series_service import sync_jellyfin_watched_series

router = APIRouter(tags=["Jellyfin"], prefix="/api/v1/jellyfin")


@router.post(
    "/import/users",
    response_model=JellyfinUsersResponse,
    response_model_exclude_none=True,
    summary="Import users from Jellyfin",
)
async def import_users(
    session: AsyncSession = Depends(get_session),
) -> JellyfinUsersResponse:
    """Import users from Jellyfin into the database."""
    result = await import_jellyfin_users(session)
    return result


@router.post(
    "/import/movies",
    response_model=JellyfinImportMoviesResponse,
    response_model_exclude_none=True,
    summary="Import movies from Jellyfin",
)
async def import_movies(
    session: AsyncSession = Depends(get_session),
) -> JellyfinImportMoviesResponse:
    """Import movies from Jellyfin"""
    result = await import_jellyfin_movies(session)
    return result


@router.post(
    "/import/series",
    response_model=JellyfinImportSeriesResponse,
    response_model_exclude_none=True,
    summary="Import series from Jellyfin",
)
async def import_series(
    session: AsyncSession = Depends(get_session),
) -> JellyfinImportSeriesResponse:
    """Import series from Jellyfin"""
    result = await import_jellyfin_series(session)
    return result


@router.post(
    "/movies/watched",
    response_model=JellyfinWatchedMoviesResponse,
    response_model_exclude_none=True,
    summary="Sync watched movies from Jellyfin by all users",
)
async def watched_movies(
    session: AsyncSession = Depends(get_session),
) -> JellyfinWatchedMoviesResponse:
    """Sync watched movies from Jellyfin by all users"""
    result = await sync_jellyfin_watched_movies(session)
    return result


@router.post(
    "/series/watched",
    response_model=JellyfinWatchedSeriesResponse,
    response_model_exclude_none=True,
    summary="Sync watched series from Jellyfin by all users",
)
async def watched_series(
    session: AsyncSession = Depends(get_session),
) -> JellyfinWatchedSeriesResponse:
    """Sync watched series from Jellyfin by all users"""
    result = await sync_jellyfin_watched_series(session)
    return result
