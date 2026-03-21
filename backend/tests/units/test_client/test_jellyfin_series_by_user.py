from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.jellyfin_client import (
    JellyfinClientError,
    fetch_jellyfin_episodes_for_user_all,
)
from app.schemas.error_codes import JellyfinErrorCode

TEST_URL = "http://jellyfin.test"
TEST_API_KEY = "test-key"


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_pagination(mock_httpx_client):
    """Пагинация: 2 страницы → все эпизоды."""
    page1 = {
        "Items": [{"Id": f"e{i}", "Name": f"Episode {i}"} for i in range(1, 101)],
        "TotalRecordCount": 150,
    }
    page2 = {
        "Items": [{"Id": f"e{i}", "Name": f"Episode {i}"} for i in range(101, 151)],
        "TotalRecordCount": 150,
    }

    resp1 = Mock()
    resp1.raise_for_status.return_value = None
    resp1.json.return_value = page1

    resp2 = Mock()
    resp2.raise_for_status.return_value = None
    resp2.json.return_value = page2

    client_instance = AsyncMock()
    client_instance.get.side_effect = [resp1, resp2]
    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    result = await fetch_jellyfin_episodes_for_user_all(TEST_URL, TEST_API_KEY, "user123")

    assert len(result) == 150
    assert result[0]["Id"] == "e1"
    assert result[-1]["Id"] == "e150"
    assert client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_single_page(mock_httpx_client):
    data = {
        "Items": [{"Id": "e1", "Name": "Pilot"}],
        "TotalRecordCount": 1,
    }

    resp = Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = data

    client_instance = AsyncMock()
    client_instance.get.return_value = resp
    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    result = await fetch_jellyfin_episodes_for_user_all(TEST_URL, TEST_API_KEY, "user123")

    assert result == [{"Id": "e1", "Name": "Pilot"}]
    assert client_instance.get.call_count == 1


@pytest.mark.parametrize(
    "error_type,status_code,error_message,expected_code",
    [
        ("network", None, "Timeout", JellyfinErrorCode.NETWORK_ERROR),
        ("http", 403, "Forbidden", JellyfinErrorCode.FETCH_FAILED),
        ("http", 500, "Internal Server Error", JellyfinErrorCode.FETCH_FAILED),
    ],
    ids=["network_error", "http_403", "http_500"],
)
@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_errors(
    mock_httpx_client,
    error_type: str,
    status_code: int | None,
    error_message: str,
    expected_code: JellyfinErrorCode,
):
    """Тесты для различных типов ошибок при fetch_jellyfin_episodes_for_user_all."""
    client_instance = AsyncMock()

    if error_type == "network":
        client_instance.get.side_effect = httpx.RequestError(error_message)
    else:
        resp = Mock()
        resp.status_code = status_code
        resp.text = error_message
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            str(status_code),
            request=Mock(),
            response=resp,
        )
        client_instance.get.return_value = resp

    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    with pytest.raises(JellyfinClientError) as exc:
        await fetch_jellyfin_episodes_for_user_all(TEST_URL, TEST_API_KEY, "user123")

    assert exc.value.code == expected_code
    if error_type == "http":
        assert error_message in exc.value.message
