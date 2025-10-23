from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.jellyfin import JellyfinUsersResponse
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
