from fastapi import APIRouter
from app.services.radarr_service import import_radarr_movies
from app.api.error_handler import handle_api_errors  # декоратор для обработки ошибок

router = APIRouter(tags=["Radarr"])

@router.post("/import", summary="Import movies from Radarr")
@handle_api_errors
async def import_radarr():
    """Import movies from Radarr into the database."""
    count = await import_radarr_movies()
    return {"status": "ok", "imported": count}
