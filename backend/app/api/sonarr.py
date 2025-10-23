from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_handler import handle_api_errors
from app.config import logger
from app.database import get_session
from app.schemas.sonarr import SonarrImportResponse
from app.services.sonarr_service import import_sonarr_series

router = APIRouter(tags=["Sonarr"], prefix="/api/v1/sonarr")


@handle_api_errors
@router.post("/import", response_model=SonarrImportResponse, summary="Import series from Sonarr")
async def import_sonarr(
    session: AsyncSession = Depends(get_session),
) -> SonarrImportResponse:
    """Import series from Sonarr into the database."""
    logger.info("Post Sonarr series import...")
    result = await import_sonarr_series(session)
    return result
