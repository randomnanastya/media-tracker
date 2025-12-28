from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import JellyfinErrorCode
from app.schemas.jellyfin import JellyfinMoviesSyncResponse
from app.schemas.responses import ErrorDetail


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_success(
    async_client, override_session_dependency, mock_session
):
    """Успешная синхронизация фильмов."""
    expected_response = JellyfinMoviesSyncResponse(
        status="success",
        synced_count=3,
        updated_count=2,
        added_count=1,
    ).model_dump(mode="json", exclude_none=True)

    with patch("app.api.jellyfin.sync_jellyfin_movies", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = expected_response

        response = await async_client.post("/api/v1/jellyfin/sync/movies")

        assert response.status_code == 200
        assert response.json() == expected_response
        mock_service.assert_awaited_once_with(mock_session)


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_network_error(
    async_client, override_session_dependency, mock_session
):
    """ClientError(NETWORK_ERROR) → 502"""
    with patch("app.api.jellyfin.sync_jellyfin_movies", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = ClientError(
            code=JellyfinErrorCode.NETWORK_ERROR, message="Jellyfin unreachable"
        )

        response = await async_client.post("/api/v1/jellyfin/sync/movies")

        assert response.status_code == 502

        exp_resp = ErrorDetail(
            code=JellyfinErrorCode.NETWORK_ERROR, message="Jellyfin unreachable"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_timeout(
    async_client, override_session_dependency, mock_session
):
    """ClientError(TIMEOUT_ERROR) → 504"""
    with patch("app.api.jellyfin.sync_jellyfin_movies", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = ClientError(
            code=JellyfinErrorCode.TIMEOUT_ERROR, message="Request timed out"
        )

        response = await async_client.post("/api/v1/jellyfin/sync/movies")

        assert response.status_code == 504

        exp_resp = ErrorDetail(
            code=JellyfinErrorCode.TIMEOUT_ERROR, message="Request timed out"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_db_conflict(
    async_client, override_session_dependency, mock_session
):
    """IntegrityError → 409"""
    from sqlalchemy.exc import IntegrityError

    with patch("app.api.jellyfin.sync_jellyfin_movies", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = IntegrityError(
            statement=None, params=None, orig=Exception("Unique violation")
        )

        response = await async_client.post("/api/v1/jellyfin/sync/movies")

        assert response.status_code == 409
        assert response.json()["message"] == "Database conflict: duplicate or invalid data"


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_generic_db_error(
    async_client, override_session_dependency, mock_session
):
    """SQLAlchemyError → 500"""
    with patch("app.api.jellyfin.sync_jellyfin_movies", new_callable=AsyncMock) as mock_service:
        mock_service.side_effect = SQLAlchemyError("Connection lost")

        response = await async_client.post("/api/v1/jellyfin/sync/movies")

        assert response.status_code == 500

        exp_resp = ErrorDetail(
            code=JellyfinErrorCode.DATABASE_ERROR, message="Database operation failed"
        ).model_dump(mode="json", exclude_none=True)

        assert response.json() == exp_resp


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_unhandled_exception():
    """Test that unhandled exceptions are caught by our handler."""
    from fastapi import Request

    from app.exceptions.handlers import handle_generic_error

    # Создаем полный scope для Request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/jellyfin/sync/movies",
        "headers": [],  # Обязательное поле
        "query_string": b"",  # Обязательное поле
        "server": ("testserver", 80),  # Обязательное поле
        "scheme": "http",
    }

    request = Request(scope=scope)
    exc = ValueError("Invalid state")

    response = await handle_generic_error(request, exc)

    assert response.status_code == 500

    # Декодируем тело ответа и проверяем структуру
    response_body = response.body.decode()
    import json

    response_data = json.loads(response_body)

    exp_resp = ErrorDetail(
        code=JellyfinErrorCode.INTERNAL_ERROR, message="Internal server error"
    ).model_dump(mode="json", exclude_none=True)

    assert response_data == exp_resp
