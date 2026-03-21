from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.jellyfin_client import (
    JellyfinClientError,
    fetch_jellyfin_series,
)
from app.schemas.error_codes import JellyfinErrorCode


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_pagination(mock_httpx_client: Mock, mock_env_vars) -> None:
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

    with (mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="token"),):
        result = await fetch_jellyfin_series()

    assert len(result) == 150
    assert result[0]["Id"] == "s1"
    assert result[-1]["Id"] == "s150"
    assert client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_single_page(mock_httpx_client: Mock, mock_env_vars) -> None:
    """Одна страница сериалов."""
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

    with (mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="token"),):
        result = await fetch_jellyfin_series()

    assert result == [{"Id": "s1", "Name": "Single Series"}]
    assert client_instance.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_no_api_key(clear_env) -> None:
    """Тест отсутствия API ключа."""
    with pytest.raises(JellyfinClientError) as exc:
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_fetch_jellyfin_series_no_url(clear_env) -> None:
    """Тест отсутствия URL Jellyfin."""
    with pytest.raises(JellyfinClientError) as exc:
        await fetch_jellyfin_series()

    assert exc.value.code == JellyfinErrorCode.INTERNAL_ERROR


@pytest.mark.parametrize(
    "error_type,status_code,error_message,expected_code",
    [
        ("network", None, "Timeout", JellyfinErrorCode.NETWORK_ERROR),
        ("http", 403, "Forbidden", JellyfinErrorCode.FETCH_FAILED),
        ("http", 404, "Not Found", JellyfinErrorCode.FETCH_FAILED),
    ],
    ids=["network_error", "http_403", "http_404"],
)
@pytest.mark.asyncio
async def test_fetch_jellyfin_series_errors(
    mock_httpx_client: Mock,
    mock_env_vars,
    error_type: str,
    status_code: int | None,
    error_message: str,
    expected_code: JellyfinErrorCode,
) -> None:
    """Тесты для различных типов ошибок при fetch_jellyfin_series."""
    client_instance = AsyncMock()

    if error_type == "network":
        client_instance.get.side_effect = httpx.RequestError(error_message)
    else:
        resp = Mock()
        resp.status_code = status_code
        resp.text = error_message
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            str(status_code),
            request=Mock(),
            response=resp,
        )
        client_instance.get.return_value = resp

    mock_httpx_client.return_value.__aenter__.return_value = client_instance

    with (
        mock_env_vars(JELLYFIN_URL="http://jf.local", JELLYFIN_API_KEY="token"),
        pytest.raises(JellyfinClientError) as exc,
    ):
        await fetch_jellyfin_series()

    assert exc.value.code == expected_code
    if error_type == "http":
        assert error_message in exc.value.message
