from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_handler import handle_api_errors
from app.database import get_session
from app.services.radarr_service import import_radarr_movies

router = APIRouter(tags=["Radarr"])


@router.post("/import", summary="Import movies from Radarr")
@handle_api_errors
async def import_radarr(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Import movies from Radarr into the database."""
    count = await import_radarr_movies(session)
    return {"status": "success", "imported_count": count}
