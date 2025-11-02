import os
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.sonarr_client import SonarrClientError, fetch_sonarr_episodes, fetch_sonarr_series
from app.schemas.error_codes import SonarrErrorCode


@pytest.mark.asyncio
async def test_fetch_sonarr_series_401_error():
    """Test fetch_sonarr_series handles 401 Unauthorized error."""
    with (
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
        patch("app.client.sonarr_client.SONARR_URL", "http://localhost:8989"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.HTTPStatusError(
            message="Unauthorized",
            request=Mock(),
            response=Mock(status_code=401, text="Invalid API key"),
        )
        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()
        assert "API error: Invalid API key" in str(exc_info.value)
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_sonarr_series_timeout():
    """Test fetch_sonarr_series handles request timeout."""
    with (
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
        patch("app.client.sonarr_client.SONARR_URL", "http://localhost:8989"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.RequestError("Request timed out", request=Mock())

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()

        assert exc_info.value.code == SonarrErrorCode.NETWORK_ERROR
        assert exc_info.value.message == "Failed to connect to Sonarr"


@pytest.mark.asyncio
async def test_fetch_sonarr_series_no_api_key():
    """Test fetch_sonarr_series fails when SONARR_API_KEY is not set."""
    with patch.dict(os.environ, {"SONARR_API_KEY": ""}, clear=True):
        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()
        assert exc_info.value.code == SonarrErrorCode.INTERNAL_ERROR
        assert exc_info.value.message == "Sonarr API key is not configured"


@pytest.mark.asyncio
async def test_fetch_sonarr_episodes_404_error():
    """Test fetch_sonarr_episodes handles 404 Not Found error."""
    with (
        patch("app.client.sonarr_client.SONARR_API_KEY", "test_key"),
        patch("app.client.sonarr_client.SONARR_URL", "http://localhost:8989"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.HTTPStatusError(
            message="Not Found",
            request=Mock(),
            response=Mock(status_code=404, text="Series not found"),
        )

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_episodes(series_id=1)

        assert exc_info.value.code == SonarrErrorCode.FETCH_FAILED
        assert exc_info.value.message == "Sonarr API error: Series not found"
