from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.radarr_service import import_radarr_movies
from app.api.error_handler import handle_api_errors  # декоратор для обработки ошибок

router = APIRouter(tags=["Radarr"])

@router.post("/import", summary="Import movies from Radarr")
@handle_api_errors
async def import_radarr(session: AsyncSession = Depends(get_session)):
    """Import movies from Radarr into the database."""
    count = await import_radarr_movies(session)  # ✅ передаём реальный AsyncSession
    return {"status": "ok", "imported": count}
