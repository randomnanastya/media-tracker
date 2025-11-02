from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.jellyfin_client import JellyfinClientError, fetch_jellyfin_users
from app.schemas.error_codes import JellyfinErrorCode


@pytest.mark.asyncio
async def test_fetch_jellyfin_users_success(mock_httpx_client):
    """Успешное получение пользователей."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"Id": "u1", "Name": "Alice"},
        {"Id": "u2", "Name": "Bob"},
    ]

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        result = await fetch_jellyfin_users()

        assert len(result) == 2
        assert result[0]["Name"] == "Alice"
        mock_client_instance.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_jellyfin_users_no_api_key():
    """Нет JELLYFIN_API_KEY → INTERNAL_ERROR."""
    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", None),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_users()

        assert exc_info.value.code == JellyfinErrorCode.INTERNAL_ERROR
        assert "API key is not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_jellyfin_users_no_url():
    """Нет JELLYFIN_URL → INTERNAL_ERROR."""
    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", None),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_users()

        assert exc_info.value.code == JellyfinErrorCode.INTERNAL_ERROR
        assert "URL is not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_jellyfin_users_network_error(mock_httpx_client):
    """httpx.RequestError → NETWORK_ERROR."""
    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = httpx.RequestError("Connection failed")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_users()

        assert exc_info.value.code == JellyfinErrorCode.NETWORK_ERROR
        assert "Failed to connect" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_jellyfin_users_http_error(mock_httpx_client):
    """HTTP 401 → FETCH_FAILED."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="401", request=Mock(), response=mock_response
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_users()

        assert exc_info.value.code == JellyfinErrorCode.FETCH_FAILED
        assert "Unauthorized" in exc_info.value.message
