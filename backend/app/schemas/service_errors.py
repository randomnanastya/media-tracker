from app.schemas.error_codes import SonarrErrorCode


class ServiceError(Exception):
    """Base exception for service-layer errors."""

    def __init__(self, code, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class SonarrServiceError(ServiceError):
    def __init__(self, code: SonarrErrorCode, message: str):
        super().__init__(code, message)
