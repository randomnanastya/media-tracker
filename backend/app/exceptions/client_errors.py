from app.schemas.error_codes import ErrorCode, JellyfinErrorCode, RadarrErrorCode, SonarrErrorCode


class ClientError(Exception):
    """Base exception for client errors."""

    def __init__(
        self, code: ErrorCode | SonarrErrorCode | RadarrErrorCode | JellyfinErrorCode, message: str
    ):
        self.code = code
        self.message = message
        super().__init__(code, message)
