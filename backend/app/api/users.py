from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.users import JellyfinUserResponse
from app.services import users_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[JellyfinUserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> list[JellyfinUserResponse]:
    users = await users_service.get_jellyfin_users(session)
    return [
        JellyfinUserResponse(
            id=user.id,
            username=user.username,
            jellyfin_user_id=user.jellyfin_user_id,
        )
        for user in users
    ]
