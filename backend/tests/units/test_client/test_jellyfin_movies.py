from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.jellyfin_client import JellyfinClientError, fetch_jellyfin_movies_for_user
from app.schemas.error_codes import JellyfinErrorCode


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_pagination(mock_httpx_client):
    """Пагинация: 2 страницы → все фильмы."""
    # Страница 1: 100 элементов, total = 150 → продолжить
    page1 = {
        "Items": [{"Id": f"m{i}", "Name": f"Movie {i}"} for i in range(1, 101)],
        "TotalRecordCount": 150,
    }
    # Страница 2: 50 элементов, total = 150 → остановиться
    page2 = {
        "Items": [{"Id": f"m{i}", "Name": f"Movie {i}"} for i in range(101, 151)],
        "TotalRecordCount": 150,
    }

    mock_response1 = Mock()
    mock_response1.status_code = 200
    mock_response1.json.return_value = page1

    mock_response2 = Mock()
    mock_response2.status_code = 200
    mock_response2.json.return_value = page2

    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = [mock_response1, mock_response2]
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        result = await fetch_jellyfin_movies_for_user("user1")

        assert len(result) == 150
        assert result[0]["Name"] == "Movie 1"
        assert result[99]["Name"] == "Movie 100"
        assert result[149]["Name"] == "Movie 150"
        assert mock_client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_single_page(mock_httpx_client):
    """Одна страница — всё ок."""
    data = {
        "Items": [{"Id": "m1", "Name": "Single Movie"}],
        "TotalRecordCount": 1,
    }
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = data

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        result = await fetch_jellyfin_movies_for_user("user1")

        assert len(result) == 1
        assert mock_client_instance.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_network_error(mock_httpx_client):
    """Сетевая ошибка → NETWORK_ERROR."""
    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = httpx.RequestError("Timeout")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_movies_for_user("user1")

        assert exc_info.value.code == JellyfinErrorCode.NETWORK_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_http_404(mock_httpx_client):
    """404 → FETCH_FAILED."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="404", request=Mock(), response=mock_response
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with (
        patch("app.client.jellyfin_client.JELLYFIN_URL", "http://jf.local"),
        patch("app.client.jellyfin_client.JELLYFIN_API_KEY", "abc123"),
    ):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_movies_for_user("user1")

        assert exc_info.value.code == JellyfinErrorCode.FETCH_FAILED
        assert "Not Found" in exc_info.value.message
