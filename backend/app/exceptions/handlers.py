import os
from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError, RequestError, TimeoutException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import (
    ErrorCode,
    JellyfinErrorCode,
    RadarrErrorCode,
    SonarrErrorCode,
)
from app.schemas.responses import ErrorDetail
from app.schemas.service_errors import SonarrServiceError


def _get_status_by_code(
    code_enum: ErrorCode | SonarrErrorCode | RadarrErrorCode | JellyfinErrorCode,
) -> int:
    """Определяет HTTP-статус по Enum-объекту ошибки."""
    code_str = code_enum.value  # ← .value — это строка
    if code_str.endswith("RATE_LIMIT_ERROR"):
        return 429
    if code_str.endswith("NETWORK_ERROR"):
        return 502
    if code_str.endswith("TIMEOUT_ERROR"):
        return 504
    if code_str.startswith(("SONARR_", "RADARR_", "JELLYFIN_")):
        return 400
    return 500


def _get_service_code(
    path: str, mapping: dict[str, Any]
) -> ErrorCode | RadarrErrorCode | SonarrErrorCode | JellyfinErrorCode:
    """Возвращает Enum-объект по пути."""
    lower_path = path.lower()
    if "radarr" in lower_path:
        return mapping.get("radarr")
    if "sonarr" in lower_path:
        return mapping.get("sonarr")
    if "jellyfin" in lower_path:
        return mapping.get("jellyfin")
    return mapping.get("default", ErrorCode.INTERNAL_ERROR)


async def handle_generic_error(request: Request, exc: Exception) -> Response:
    logger.exception("Unexpected error on %s: %s", request.url.path, exc)
    code = _get_service_code(
        request.url.path,
        {
            "radarr": RadarrErrorCode.INTERNAL_ERROR,
            "sonarr": SonarrErrorCode.INTERNAL_ERROR,
            "jellyfin": JellyfinErrorCode.INTERNAL_ERROR,
            "default": ErrorCode.INTERNAL_ERROR,
        },
    )
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(code=code, message="Internal server error").model_dump(
            exclude_none=True
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClientError)
    async def handle_client_error(request: Request, exc: ClientError) -> Response:
        logger.error(
            "%s client error on %s: %s", exc.__class__.__name__, request.url.path, exc.message
        )
        status_code = _get_status_by_code(exc.code)  # ← передаём Enum
        return JSONResponse(
            status_code=status_code,
            content=ErrorDetail(code=exc.code, message=exc.message).model_dump(
                exclude_none=True
            ),  # ← Enum
        )

    @app.exception_handler(RequestError)
    async def handle_request_error(request: Request, exc: RequestError) -> Response:
        logger.error("Network error during API call on %s: %s", request.url.path, exc)
        code = _get_service_code(
            request.url.path,
            {
                "radarr": RadarrErrorCode.NETWORK_ERROR,
                "sonarr": SonarrErrorCode.NETWORK_ERROR,
                "jellyfin": JellyfinErrorCode.NETWORK_ERROR,
                "default": ErrorCode.NETWORK_ERROR,
            },
        )
        return JSONResponse(
            status_code=502,
            content=ErrorDetail(
                code=code, message="Failed to connect to external service"
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(TimeoutException)
    async def handle_timeout_error(request: Request, exc: TimeoutException) -> Response:
        logger.error("Timeout during API call on %s: %s", request.url.path, exc)
        code = _get_service_code(
            request.url.path,
            {
                "radarr": RadarrErrorCode.TIMEOUT_ERROR,
                "sonarr": SonarrErrorCode.TIMEOUT_ERROR,
                "jellyfin": JellyfinErrorCode.TIMEOUT_ERROR,
                "default": ErrorCode.TIMEOUT_ERROR,
            },
        )
        return JSONResponse(
            status_code=504,
            content=ErrorDetail(
                code=code, message="Request to external service timed out"
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(HTTPStatusError)
    async def handle_http_status_error(request: Request, exc: HTTPStatusError) -> Response:
        logger.error(
            "External API error on %s: %s, status: %s",
            request.url.path,
            exc,
            exc.response.status_code,
        )

        external_status = exc.response.status_code

        base_code = _get_service_code(
            request.url.path,
            {
                "radarr": RadarrErrorCode.EXTERNAL_API_ERROR,
                "sonarr": SonarrErrorCode.FETCH_FAILED,
                "jellyfin": JellyfinErrorCode.FETCH_FAILED,
                "default": ErrorCode.INTERNAL_ERROR,
            },
        )

        if external_status == 429:
            code = _get_service_code(
                request.url.path,
                {
                    "radarr": RadarrErrorCode.RATE_LIMIT_ERROR,
                    "sonarr": SonarrErrorCode.RATE_LIMIT_ERROR,
                    "jellyfin": JellyfinErrorCode.RATE_LIMIT_ERROR,
                    "default": ErrorCode.RATE_LIMIT_ERROR,
                },
            )
            status_code = 429
        elif 400 <= external_status < 500:
            code = base_code
            status_code = 424
        else:
            code = base_code
            status_code = 503

        debug_msg = f" (status: {external_status})" if os.getenv("APP_ENV") == "development" else ""
        message = f"External service error{debug_msg}"

        return JSONResponse(
            status_code=status_code,
            content=ErrorDetail(code=code, message=message).model_dump(exclude_none=True),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, exc: SQLAlchemyError) -> Response:
        logger.error("Database error on %s: %s", request.url.path, exc)

        if isinstance(exc, IntegrityError):
            code = _get_service_code(
                request.url.path,
                {
                    "radarr": RadarrErrorCode.DATABASE_ERROR,
                    "sonarr": SonarrErrorCode.DATABASE_ERROR,
                    "jellyfin": JellyfinErrorCode.DATABASE_ERROR,
                    "default": ErrorCode.DATABASE_ERROR,
                },
            )
            message = "Database conflict: duplicate or invalid data"
            status_code = 409
        else:
            code = _get_service_code(
                request.url.path,
                {
                    "radarr": RadarrErrorCode.DATABASE_ERROR,
                    "sonarr": SonarrErrorCode.DATABASE_ERROR,
                    "jellyfin": JellyfinErrorCode.DATABASE_ERROR,
                    "default": ErrorCode.DATABASE_ERROR,
                },
            )
            message = "Database operation failed"
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content=ErrorDetail(code=code, message=message).model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        details = [
            {"loc": " → ".join(map(str, err["loc"])), "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid request data",
                details=details,
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(JSONDecodeError)
    async def handle_json_decode_error(request: Request, exc: JSONDecodeError) -> Response:
        logger.error("JSON parse error on %s: %s", request.url.path, exc)
        code = _get_service_code(
            request.url.path,
            {
                "radarr": RadarrErrorCode.INTERNAL_ERROR,
                "sonarr": SonarrErrorCode.INTERNAL_ERROR,
                "jellyfin": JellyfinErrorCode.INTERNAL_ERROR,
                "default": ErrorCode.INTERNAL_ERROR,
            },
        )
        return JSONResponse(
            status_code=502,
            content=ErrorDetail(
                code=code, message="Invalid response from external service"
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(SonarrServiceError)
    async def handle_service_error(request: Request, exc: SonarrServiceError):
        logger.error("Unhandled service error: %s. Request url %s", exc.message, request.url)
        return JSONResponse(
            status_code=500,
            content=ErrorDetail(code=exc.code, message=exc.message).model_dump(exclude_none=True),
        )
