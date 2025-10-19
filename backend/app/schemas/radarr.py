from pydantic import BaseModel

from app.schemas.responses import ErrorDetail


class RadarrImportResponse(BaseModel):
    status: str = "success"
    imported_count: int = 0
    error: ErrorDetail | None = None
