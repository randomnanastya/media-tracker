from pydantic import BaseModel

from app.schemas.responses import ErrorDetail


class SonarrImportResponse(BaseModel):
    new_series: int = 0
    updated_series: int = 0
    new_episodes: int = 0
    updated_episodes: int = 0
    error: ErrorDetail | None = None
