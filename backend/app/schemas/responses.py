from pydantic import BaseModel

from app.schemas.error_codes import (
    ErrorCode,
    JellyfinErrorCode,
    RadarrErrorCode,
    SonarrErrorCode,
    TmdbBridgeErrorCode,
)


class ErrorDetail(BaseModel):
    code: ErrorCode | SonarrErrorCode | RadarrErrorCode | JellyfinErrorCode | TmdbBridgeErrorCode
    message: str
    details: list[dict[str, str]] | None = None
