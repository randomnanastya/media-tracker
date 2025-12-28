from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.sonarr import SonarrImportResponse
from app.services.sonarr_service import import_sonarr_series

router = APIRouter(tags=["Sonarr"], prefix="/api/v1/sonarr")


@router.post(
    "/import",
    response_model=SonarrImportResponse,
    response_model_exclude_none=True,
    summary="Import series from Sonarr",
)
async def import_sonarr(
    session: AsyncSession = Depends(get_session),
) -> SonarrImportResponse:
    """Import series from Sonarr into the database."""
    result = await import_sonarr_series(session)
    return result
