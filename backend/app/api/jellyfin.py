from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.jellyfin import JellyfinMoviesSyncResponse, JellyfinUsersResponse
from app.services.jellyfin_movies_service import sync_jellyfin_movies
from app.services.jellyfin_users_service import import_jellyfin_users

router = APIRouter(tags=["Jellyfin"], prefix="/api/v1/jellyfin")


@router.post(
    "/import/users", response_model=JellyfinUsersResponse, summary="Import users from Jellyfin"
)
async def import_users(
    session: AsyncSession = Depends(get_session),
) -> JellyfinUsersResponse:
    """Import users from Jellyfin into the database."""
    result = await import_jellyfin_users(session)
    return result


@router.post(
    "/sync/movies",
    response_model=JellyfinMoviesSyncResponse,
    summary="Sync watched movies from Jellyfin",
)
async def sync_movies(
    session: AsyncSession = Depends(get_session),
) -> JellyfinMoviesSyncResponse:
    """Sync watched status for all users from Jellyfin."""
    result = await sync_jellyfin_movies(session)
    return result
