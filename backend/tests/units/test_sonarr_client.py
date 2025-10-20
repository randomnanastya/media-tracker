import os
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.sonarr_client import fetch_sonarr_episodes, fetch_sonarr_series


@pytest.mark.asyncio
async def test_fetch_sonarr_series_401_error():
    """Test fetch_sonarr_series handles 401 Unauthorized error."""
    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
    ):
        mock_get.side_effect = httpx.HTTPStatusError(
            message="Unauthorized",
            request=Mock(),
            response=Mock(status_code=401, text="Invalid API key"),
        )
        with pytest.raises(ValueError) as exc_info:
            await fetch_sonarr_series()
        assert "API error: Invalid API key" in str(exc_info.value)
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_sonarr_series_timeout():
    """Test fetch_sonarr_series handles request timeout."""
    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
    ):
        mock_get.side_effect = httpx.RequestError("Request timed out", request=Mock())
        with pytest.raises(ValueError) as exc_info:
            await fetch_sonarr_series()

        assert "Client network error: Request timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_sonarr_series_no_api_key():
    """Test fetch_sonarr_series fails when SONARR_API_KEY is not set."""
    with patch.dict(os.environ, {"SONARR_API_KEY": ""}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await fetch_sonarr_series()
        assert "SONARR_API_KEY is not set" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_sonarr_episodes_404_error():
    """Test fetch_sonarr_episodes handles 404 Not Found error."""
    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
    ):
        mock_get.side_effect = httpx.HTTPStatusError(
            message="Not Found",
            request=Mock(),
            response=Mock(status_code=404, text="Series not found"),
        )

        with pytest.raises(ValueError) as exc_info:
            await fetch_sonarr_episodes(series_id=1)
        assert "API error: Series not found" in str(exc_info.value)
