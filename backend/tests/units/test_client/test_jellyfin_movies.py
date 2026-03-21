from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.jellyfin_client import JellyfinClientError, fetch_jellyfin_movies
from app.schemas.error_codes import JellyfinErrorCode


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_pagination(mock_httpx_client: Mock, mock_env_vars) -> None:
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

    # Патчим os.getenv для декоратора @validate_config и глобальные переменные модуля для функции
    with (mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="abc123"),):
        result = await fetch_jellyfin_movies()

        assert len(result) == 150
        assert result[0]["Name"] == "Movie 1"
        assert result[99]["Name"] == "Movie 100"
        assert result[149]["Name"] == "Movie 150"
        assert mock_client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_single_page(mock_httpx_client: Mock, mock_env_vars) -> None:
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

    with (mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="abc123"),):
        result = await fetch_jellyfin_movies()

        assert len(result) == 1
        assert mock_client_instance.get.call_count == 1


@pytest.mark.parametrize(
    "error_type,status_code,error_message,expected_code",
    [
        ("network", None, "Timeout", JellyfinErrorCode.NETWORK_ERROR),
        ("http", 404, "Not Found", JellyfinErrorCode.FETCH_FAILED),
        ("http", 500, "Internal Server Error", JellyfinErrorCode.FETCH_FAILED),
    ],
    ids=["network_error", "http_404", "http_500"],
)
@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_errors(
    mock_httpx_client: Mock,
    mock_env_vars,
    error_type: str,
    status_code: int | None,
    error_message: str,
    expected_code: JellyfinErrorCode,
) -> None:
    """Тесты для различных типов ошибок при fetch_jellyfin_movies."""
    mock_client_instance = AsyncMock()

    if error_type == "network":
        # Сетевая ошибка
        mock_client_instance.get.side_effect = httpx.RequestError(error_message)
    else:
        # HTTP ошибка
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = error_message
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=str(status_code), request=Mock(), response=mock_response
        )
        mock_client_instance.get.return_value = mock_response

    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="abc123"):
        with pytest.raises(JellyfinClientError) as exc_info:
            await fetch_jellyfin_movies()

        assert exc_info.value.code == expected_code
        if error_type == "http":
            assert error_message in exc_info.value.message
