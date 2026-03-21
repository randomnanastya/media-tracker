from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.radarr_client import RadarrClientError, fetch_radarr_movies
from app.schemas.error_codes import RadarrErrorCode


@pytest.mark.asyncio
async def test_fetch_radarr_movies_no_config(clear_env) -> None:
    """Test when RADARR_URL and RADARR_API_KEY are not set."""
    with pytest.raises(RadarrClientError) as exc_info:
        await fetch_radarr_movies()

    assert exc_info.value.code == RadarrErrorCode.INTERNAL_ERROR
    assert "is not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_success(mock_env_vars) -> None:
    """Test successful fetch with valid response."""
    mock_movies = [{"id": 1, "title": "Test Movie"}]
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_movies

    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = await fetch_radarr_movies()

        assert result == mock_movies
        mock_client_instance.__aenter__.return_value.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_radarr_movies_network_error(mock_env_vars) -> None:
    """Test network-level error (RequestError)."""
    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
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
async def test_fetch_radarr_movies_timeout(mock_env_vars) -> None:
    """Test timeout error."""
    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
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


@pytest.mark.parametrize(
    "status_code,error_text",
    [
        (404, "Not found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ],
)
async def test_fetch_radarr_movies_http_errors(
    mock_env_vars, status_code: int, error_text: str
) -> None:
    """Тесты для HTTP ошибок от Radarr."""
    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):

        mock_get.side_effect = httpx.HTTPStatusError(
            message="Server error",
            request=Mock(),
            response=Mock(status_code=status_code, text=error_text),
        )

        with pytest.raises(RadarrClientError) as exc_info:
            await fetch_radarr_movies()

        assert exc_info.value.code == RadarrErrorCode.EXTERNAL_API_ERROR
        assert error_text in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_radarr_movies_invalid_json(mock_env_vars) -> None:
    """Test when response is not valid JSON."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
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
async def test_fetch_radarr_movies_unexpected_exception(mock_env_vars) -> None:
    """Test any unexpected exception during client creation or request."""
    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (
        mock_env_vars(RADARR_URL="http://localhost:7878", RADARR_API_KEY="test_key"),
        patch("app.client.radarr_client.RADARR_URL", "http://localhost:7878"),
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
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
