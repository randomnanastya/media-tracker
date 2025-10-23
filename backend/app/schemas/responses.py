from pydantic import BaseModel

from app.schemas.error_codes import JellyfinErrorCode, RadarrErrorCode, SonarrErrorCode


class ErrorDetail(BaseModel):
    code: SonarrErrorCode | RadarrErrorCode | JellyfinErrorCode
    message: str
