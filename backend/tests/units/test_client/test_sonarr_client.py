from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.sonarr_client import SonarrClientError, fetch_sonarr_series
from app.schemas.error_codes import SonarrErrorCode


@pytest.mark.asyncio
async def test_fetch_sonarr_series_timeout(mock_env_vars) -> None:
    """Test fetch_sonarr_series handles request timeout."""
    with (
        mock_env_vars(SONARR_URL="http://localhost:8989", SONARR_API_KEY="test_key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.RequestError("Request timed out", request=Mock())

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()

        assert exc_info.value.code == SonarrErrorCode.NETWORK_ERROR
        assert exc_info.value.message == "Failed to connect to Sonarr"


@pytest.mark.asyncio
async def test_fetch_sonarr_series_no_api_key(mock_env_vars) -> None:
    """Test fetch_sonarr_series fails when SONARR_API_KEY is not set."""
    with (mock_env_vars(SONARR_URL="http://localhost:8989", SONARR_API_KEY=None),):
        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()
        assert exc_info.value.code == SonarrErrorCode.INTERNAL_ERROR
        assert exc_info.value.message == "Sonarr API key is not configured"


@pytest.mark.parametrize(
    "status_code,error_text",
    [
        (404, "Sonarr API error: Series not found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
        (401, "API error: Invalid API key"),
    ],
)
async def test_fetch_sonarr_series_http_errors(
    mock_env_vars, status_code: int, error_text: str
) -> None:
    """Test fetch_sonarr_series handles http errors."""
    with (
        mock_env_vars(SONARR_URL="http://localhost:8989", SONARR_API_KEY="test_key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_get.side_effect = httpx.HTTPStatusError(
            message=error_text,
            request=Mock(),
            response=Mock(status_code=status_code, text=error_text),
        )
        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series()
        assert error_text in str(exc_info.value)
        mock_get.assert_called_once()
