from pydantic import BaseModel

from app.schemas.responses import ErrorDetail


class SonarrImportResponse(BaseModel):
    new_series: int | None = None
    updated_series: int | None = None
    new_episodes: int | None = None
    updated_episodes: int | None = None
    error: ErrorDetail | None = None
