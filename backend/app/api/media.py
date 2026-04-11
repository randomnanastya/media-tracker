from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.media import MediaListResponse
from app.services.media_service import get_media_list

router = APIRouter(prefix="/api/v1", tags=["media"])


@router.get("/media", response_model=MediaListResponse)
async def list_media(
    type: Literal["movie", "series"] | None = Query(
        default=None, description="Filter by type: movie or series"
    ),
    status: str | None = Query(default=None, description="Filter by watch status"),
    jellyfin_user_id: str | None = Query(default=None, description="Jellyfin user ID (UUID)"),
    session: AsyncSession = Depends(get_session),
) -> MediaListResponse:
    return await get_media_list(
        session=session,
        media_type=type,
        status=status,
        jellyfin_user_id=jellyfin_user_id,
    )
