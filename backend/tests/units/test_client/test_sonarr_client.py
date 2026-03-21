"""Unit tests for app.client.sonarr_client.

The client functions now accept url and api_key directly — no env vars needed.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.sonarr_client import SonarrClientError, fetch_sonarr_series
from app.schemas.error_codes import SonarrErrorCode

_URL = "http://localhost:8989"
_KEY = "test_key"


@pytest.mark.asyncio
async def test_fetch_sonarr_series_success() -> None:
    """Successful fetch returns the list of series."""
    mock_series = [{"id": 1, "title": "Test Series"}]
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_series

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = await fetch_sonarr_series(url=_URL, api_key=_KEY)

    assert result == mock_series


@pytest.mark.asyncio
async def test_fetch_sonarr_series_timeout() -> None:
    """Request timeout raises SonarrClientError with NETWORK_ERROR code."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("Request timed out", request=Mock())

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series(url=_URL, api_key=_KEY)

    assert exc_info.value.code == SonarrErrorCode.NETWORK_ERROR
    assert exc_info.value.message == "Failed to connect to Sonarr"


@pytest.mark.parametrize(
    "status_code,error_text",
    [
        (404, "Sonarr API error: Series not found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
        (401, "API error: Invalid API key"),
    ],
)
@pytest.mark.asyncio
async def test_fetch_sonarr_series_http_errors(status_code: int, error_text: str) -> None:
    """HTTP error responses from Sonarr raise SonarrClientError."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            message=error_text,
            request=Mock(),
            response=Mock(status_code=status_code, text=error_text),
        )

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series(url=_URL, api_key=_KEY)

    assert error_text in str(exc_info.value)
    mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_sonarr_series_unexpected_error() -> None:
    """Unexpected exception raises SonarrClientError with INTERNAL_ERROR."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.side_effect = RuntimeError("Totally unexpected")
        mock_client.return_value = mock_client_instance

        with pytest.raises(SonarrClientError) as exc_info:
            await fetch_sonarr_series(url=_URL, api_key=_KEY)

    assert exc_info.value.code == SonarrErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_sonarr_series_sends_api_key_header() -> None:
    """The X-Api-Key header is sent with the correct api_key value."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_get = mock_client_instance.__aenter__.return_value.get
        mock_get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        await fetch_sonarr_series(url=_URL, api_key="custom-sonarr-key")

    headers = mock_get.call_args.kwargs.get("headers", {})
    assert headers.get("X-Api-Key") == "custom-sonarr-key"
