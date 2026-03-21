from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.jellyfin_client import JellyfinClientError, fetch_jellyfin_users
from app.schemas.error_codes import JellyfinErrorCode

TEST_URL = "http://jellyfin.test"
TEST_API_KEY = "test-key"


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

    result = await fetch_jellyfin_users(TEST_URL, TEST_API_KEY)

    assert len(result) == 2
    assert result[0]["Name"] == "Alice"
    mock_client_instance.get.assert_called_once()


@pytest.mark.parametrize(
    "error_type,status_code,error_message,expected_code",
    [
        ("network", None, "Connection failed", JellyfinErrorCode.NETWORK_ERROR),
        ("http", 401, "Unauthorized", JellyfinErrorCode.FETCH_FAILED),
        ("http", 403, "Forbidden", JellyfinErrorCode.FETCH_FAILED),
    ],
    ids=["network_error", "http_401", "http_403"],
)
@pytest.mark.asyncio
async def test_fetch_jellyfin_users_errors(
    mock_httpx_client,
    error_type: str,
    status_code: int | None,
    error_message: str,
    expected_code: JellyfinErrorCode,
):
    """Тесты для различных типов ошибок при fetch_jellyfin_users."""
    mock_client_instance = AsyncMock()

    if error_type == "network":
        mock_client_instance.get.side_effect = httpx.RequestError(error_message)
    else:
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = error_message
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=str(status_code), request=Mock(), response=mock_response
        )
        mock_client_instance.get.return_value = mock_response

    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with pytest.raises(JellyfinClientError) as exc_info:
        await fetch_jellyfin_users(TEST_URL, TEST_API_KEY)

    assert exc_info.value.code == expected_code
    if error_type == "http":
        assert error_message in exc_info.value.message
