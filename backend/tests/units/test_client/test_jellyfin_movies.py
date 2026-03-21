"""Unit tests for fetch_jellyfin_movies in app.client.jellyfin_client.

The function now accepts url and api_key directly — no env vars needed.
"""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.jellyfin_client import JellyfinClientError, fetch_jellyfin_movies
from app.schemas.error_codes import JellyfinErrorCode

_URL = "http://jf.local"
_KEY = "abc123"


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_pagination(mock_httpx_client: Mock) -> None:
    """Pagination: 2 pages → all 150 movies collected."""
    page1 = {
        "Items": [{"Id": f"m{i}", "Name": f"Movie {i}"} for i in range(1, 101)],
        "TotalRecordCount": 150,
    }
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

    result = await fetch_jellyfin_movies(url=_URL, api_key=_KEY)

    assert len(result) == 150
    assert result[0]["Name"] == "Movie 1"
    assert result[99]["Name"] == "Movie 100"
    assert result[149]["Name"] == "Movie 150"
    assert mock_client_instance.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_single_page(mock_httpx_client: Mock) -> None:
    """Single page response — fetches once and returns all items."""
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

    result = await fetch_jellyfin_movies(url=_URL, api_key=_KEY)

    assert len(result) == 1
    assert mock_client_instance.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_empty_library(mock_httpx_client: Mock) -> None:
    """Empty library returns an empty list without errors."""
    data = {"Items": [], "TotalRecordCount": 0}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = data

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    result = await fetch_jellyfin_movies(url=_URL, api_key=_KEY)

    assert result == []


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
    error_type: str,
    status_code: int | None,
    error_message: str,
    expected_code: JellyfinErrorCode,
) -> None:
    """Various error conditions raise JellyfinClientError with the right code."""
    mock_client_instance = AsyncMock()

    if error_type == "network":
        mock_client_instance.get.side_effect = httpx.RequestError(error_message)
    else:
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.text = error_message
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=str(status_code), request=Mock(), response=mock_response
        )
        mock_client_instance.get.return_value = mock_response

    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    with pytest.raises(JellyfinClientError) as exc_info:
        await fetch_jellyfin_movies(url=_URL, api_key=_KEY)

    assert exc_info.value.code == expected_code
    if error_type == "http":
        assert error_message in exc_info.value.message


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_sends_api_key_in_url(mock_httpx_client: Mock) -> None:
    """The api_key is embedded in the base_url passed to the paginator."""
    data = {"Items": [], "TotalRecordCount": 0}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = data

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    await fetch_jellyfin_movies(url="http://myjf.local", api_key="my-secret-token")

    call_args = mock_client_instance.get.call_args
    # fetch_paginated calls client.get(url=..., params=...) with keyword args
    # The api_key is embedded in the base URL for Jellyfin Items endpoint
    called_url: str = call_args.kwargs.get("url", "")
    assert "my-secret-token" in called_url
    assert "myjf.local" in called_url


@pytest.mark.asyncio
async def test_fetch_jellyfin_movies_includes_provider_ids_field(mock_httpx_client: Mock) -> None:
    """Request params include ProviderIds field for external ID resolution."""
    data = {"Items": [], "TotalRecordCount": 0}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = data

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    await fetch_jellyfin_movies(url=_URL, api_key=_KEY)

    call_kwargs = mock_client_instance.get.call_args.kwargs
    params = call_kwargs.get("params", {})
    # fetch_paginated merges base params with pagination params
    assert "ProviderIds" in params.get("Fields", "")
    assert params.get("IncludeItemTypes") == "Movie"
