from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.radarr_client import RadarrClientError, fetch_radarr_movies
from app.schemas.error_codes import RadarrErrorCode


@pytest.mark.asyncio
async def test_fetch_radarr_movies_no_api_key():
    """Test when RADARR_API_KEY is not set."""
    with patch("app.client.radarr_client.RADARR_API_KEY", None):
        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
        assert exc_info.value.message == "Radarr API key is not configured"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_no_url():
    """Test when RADARR_URL is not set."""
    with (
        patch("app.client.radarr_client.RADARR_URL", None),
        patch("app.client.radarr_client.RADARR_API_KEY", "dummy"),
    ):
        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
        assert exc_info.value.message == "Radarr URL is not configured"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_success():
    """Test successful fetch with valid response."""
    mock_movies = [{"id": 1, "title": "Test Movie"}]
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_movies

    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = await fetch_radarr_movies()

        assert result == mock_movies
        mock_client_instance.__aenter__.return_value.get.assert_called_once_with(
            "http://localhost:7878/api/v3/movie",
            headers={"X-Api-Key": "test_key"},
            timeout=30.0,
        )


@pytest.mark.asyncio
async def test_fetch_radarr_movies_network_error():
    """Test network-level error (RequestError)."""
    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.side_effect = httpx.RequestError(
            "Connection failed"
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.NETWORK_ERROR
        assert exc_info.value.message == "Failed to connect to Radarr"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_timeout():
    """Test timeout error."""
    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.side_effect = httpx.TimeoutException(
            "Timed out"
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.NETWORK_ERROR
        assert exc_info.value.message == "Failed to connect to Radarr"


@pytest.mark.asyncio
async def test_fetch_radarr_movies_404_error():
    """Test 404 HTTP error."""
    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.HTTPStatusError(
            message="Not found",
            request=Mock(),
            response=Mock(status_code=404, text="Resource not found"),
        )

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.EXTERNAL_API_ERROR
        assert "Resource not found" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_500_error():
    """Test 500 HTTP error."""
    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.HTTPStatusError(
            message="Server error",
            request=Mock(),
            response=Mock(status_code=500, text="Internal Server Error"),
        )

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.EXTERNAL_API_ERROR
        assert "Internal Server Error" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_invalid_json():
    """Test when response is not valid JSON."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
        assert "Unexpected error occurred while fetching movies" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_unexpected_exception():
    """Test any unexpected exception during client creation or request."""
    with (
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("httpx.AsyncClient") as mock_client,
    ):

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.side_effect = RuntimeError("Unexpected failure in request")

        mock_client.return_value = mock_client_instance

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
        assert "Unexpected error occurred while fetching movies" in exc_info.value.message
