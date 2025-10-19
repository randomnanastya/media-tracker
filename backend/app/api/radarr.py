from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_handler import handle_api_errors
from app.database import get_session
from app.schemas.radarr import RadarrImportResponse
from app.services.radarr_service import import_radarr_movies

router = APIRouter(tags=["Radarr"], prefix="/api/v1/radarr")


@router.post("/import", response_model=RadarrImportResponse, summary="Import movies from Radarr")
@handle_api_errors
async def import_radarr(
    session: AsyncSession = Depends(get_session),
) -> RadarrImportResponse:
    """Import movies from Radarr into the database."""
    result = await import_radarr_movies(session)
    return result
