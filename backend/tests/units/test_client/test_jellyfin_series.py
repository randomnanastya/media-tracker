from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.jellyfin_client import (
    JellyfinClientError,
    fetch_jellyfin_series,
)
from app.schemas.error_codes import JellyfinErrorCode


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_pagination(mock_httpx_client):
    """Пагинация: 2 страницы → все сериалы."""
    page1 = {
        "Items": [{"Id": f"s{i}", "Name": f"Series {i}"} for i in range(1, 101)],
        "TotalRecordCount": 150,
    }
    page2 = {
        "Items": [{"Id": f"s{i}", "Name": f"Series {i}"} for i in range(101, 151)],
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
        result = await fetch_jellyfin_series()

    assert len(result) == 150
    assert result[0]["Id"] == "s1"
    assert result[-1]["Id"] == "s150"
    assert client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_single_page(mock_httpx_client):
    data = {
        "Items": [{"Id": "s1", "Name": "Single Series"}],
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
        result = await fetch_jellyfin_series()

    assert result == [{"Id": "s1", "Name": "Single Series"}]
    assert client_instance.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_no_api_key():
    """Тест отсутствия API ключа."""
    with (
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", None),
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_no_url():
    """Тест отсутствия URL Jellyfin."""
    with (
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
        patch("app.client.jellyfin_client.JELLYFIN_URL", None),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_network_error(mock_httpx_client):
    """Тест сетевой ошибки."""
    client_instance = AsyncMock()
    client_instance.get.side_effect = httpx.RequestError("Timeout")
    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "token"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.NETWORK_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_http_error(mock_httpx_client):
    """Тест HTTP ошибки (например, 403 Forbidden)."""
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
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.FETCH_FAILED
    assert "Forbidden" in exc.value.message
