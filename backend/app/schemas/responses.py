from pydantic import BaseModel

from app.schemas.error_codes import ErrorCode, JellyfinErrorCode, RadarrErrorCode, SonarrErrorCode


class ErrorDetail(BaseModel):
    code: ErrorCode | SonarrErrorCode | RadarrErrorCode | JellyfinErrorCode
    message: str
    details: list[dict] | None = None
