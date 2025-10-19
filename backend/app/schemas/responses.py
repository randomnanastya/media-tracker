from pydantic import BaseModel

from app.schemas.error_codes import RadarrErrorCode, SonarrErrorCode


class ErrorDetail(BaseModel):
    code: SonarrErrorCode | RadarrErrorCode
    message: str
