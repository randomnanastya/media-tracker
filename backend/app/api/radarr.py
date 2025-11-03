from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.radarr import RadarrImportResponse
from app.services.radarr_service import import_radarr_movies

router = APIRouter(tags=["Radarr"], prefix="/api/v1/radarr")


@router.post(
    "/import",
    response_model=RadarrImportResponse,
    response_model_exclude_none=True,
    summary="Import movies from Radarr",
)
async def import_radarr(
    session: AsyncSession = Depends(get_session),
) -> RadarrImportResponse:
    """Import movies from Radarr into the database."""
    result = await import_radarr_movies(session)
    return result
