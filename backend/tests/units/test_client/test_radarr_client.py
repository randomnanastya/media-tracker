"""Unit tests for app.client.radarr_client.

The client functions now accept url and api_key directly — no env vars needed.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.radarr_client import RadarrClientError, fetch_radarr_movies
from app.schemas.error_codes import RadarrErrorCode

_URL = "http://localhost:7878"
_KEY = "test_key"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_success() -> None:
    """Successful fetch returns the list of movies from Radarr."""
    mock_movies = [{"id": 1, "title": "Test Movie"}]
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_movies

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert result == mock_movies
    mock_client_instance.__aenter__.return_value.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_radarr_movies_network_error() -> None:
    """Network-level error raises RadarrClientError with NETWORK_ERROR code."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.side_effect = httpx.RequestError(
            "Connection failed"
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == RadarrErrorCode.NETWORK_ERROR
    assert exc_info.value.message == "Failed to connect to Radarr"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_timeout() -> None:
    """Timeout error raises RadarrClientError with NETWORK_ERROR code."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.side_effect = httpx.TimeoutException(
            "Timed out"
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == RadarrErrorCode.NETWORK_ERROR
    assert exc_info.value.message == "Failed to connect to Radarr"


@pytest.mark.parametrize(
    "status_code,error_text",
    [
        (404, "Not found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ],
)
@pytest.mark.asyncio
async def test_fetch_radarr_movies_http_errors(status_code: int, error_text: str) -> None:
    """HTTP error responses from Radarr raise RadarrClientError with EXTERNAL_API_ERROR."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            message="Server error",
            request=Mock(),
            response=Mock(status_code=status_code, text=error_text),
        )

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == RadarrErrorCode.EXTERNAL_API_ERROR
    assert error_text in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_invalid_json() -> None:
    """Non-JSON response raises RadarrClientError with INTERNAL_ERROR."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
    assert "Unexpected error occurred while fetching movies" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_unexpected_exception() -> None:
    """Unexpected exception wrapped in INTERNAL_ERROR."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.side_effect = RuntimeError("Unexpected failure in request")
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
    assert "Unexpected error occurred while fetching movies" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_sends_api_key_header() -> None:
    """The X-Api-Key header is sent with the provided api_key."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_get = mock_client_instance.__aenter__.return_value.get
        mock_get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        await fetch_radarr_movies(url=_URL, api_key="my-custom-key")

    call_kwargs = mock_get.call_args
    # fetch_paginated_simple calls client.get(url=..., headers=..., ...)
    headers = call_kwargs.kwargs.get("headers", {})
    assert headers.get("X-Api-Key") == "my-custom-key"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_uses_correct_url() -> None:
    """The request is made to the expected URL constructed from url parameter."""
    from app.client.endpoints import RADARR_MOVIES

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_get = mock_client_instance.__aenter__.return_value.get
        mock_get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        await fetch_radarr_movies(url="http://myradarr:7878", api_key=_KEY)

    call_args = mock_get.call_args
    # fetch_paginated_simple calls client.get(url=...) with keyword arg
    called_url = call_args.kwargs.get("url", "")
    assert called_url == f"http://myradarr:7878{RADARR_MOVIES}"
