from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.jellyfin_client import (
    JellyfinClientError,
    fetch_jellyfin_episodes_for_user_all,
)
from app.schemas.error_codes import JellyfinErrorCode


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

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
    ):
        result = await fetch_jellyfin_episodes_for_user_all("user123")

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

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
    ):
        result = await fetch_jellyfin_episodes_for_user_all("user123")

    assert result == [{"Id": "e1", "Name": "Pilot"}]
    assert client_instance.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_no_api_key():
    with (
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", None),
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_episodes_for_user_all("user123")

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_no_url():
    with (
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
        patch("app.client.jellyfin_client.JELLYFIN_URL", None),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_episodes_for_user_all("user123")

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_network_error(mock_httpx_client):
    client_instance = AsyncMock()
    client_instance.get.side_effect = httpx.RequestError("Timeout")
    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_episodes_for_user_all("user123")

    assert exc.value.code == JellyfinErrorCode.NETWORK_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_episodes_http_error(mock_httpx_client):
    resp = Mock()
    resp.text = "Forbidden"
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403",
        request=Mock(),
        response=resp,
    )

    client_instance = AsyncMock()
    client_instance.get.return_value = resp
    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_episodes_for_user_all("user123")

    assert exc.value.code == JellyfinErrorCode.FETCH_FAILED
    assert "Forbidden" in exc.value.message
