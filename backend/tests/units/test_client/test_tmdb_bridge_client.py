"""Unit tests for fetch_tmdb_movie in app.client.tmdb_bridge_client."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.client.tmdb_bridge_client import TmdbBridgeClientError, fetch_tmdb_movie
from app.schemas.error_codes import TmdbBridgeErrorCode

_TMDB_ID = "123"
_MOVIE_URL = "https://bridge.mediatrackr.org/tmdb/movie/123"


@pytest.mark.asyncio
async def test_fetch_tmdb_movie_200() -> None:
    """200 OK — returns parsed dict."""
    body = {"tmdb_id": "123", "title": "Test Movie"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = body
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_tmdb_movie(_TMDB_ID, client=mock_client)

    assert result == body
    mock_client.get.assert_called_once_with(_MOVIE_URL, timeout=15.0)


@pytest.mark.asyncio
async def test_fetch_tmdb_movie_404_returns_none() -> None:
    """404 — returns None without raising."""
    mock_response = Mock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_tmdb_movie(_TMDB_ID, client=mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_tmdb_movie_timeout() -> None:
    """Timeout → TmdbBridgeClientError with TIMEOUT_ERROR."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("timed out")

    with pytest.raises(TmdbBridgeClientError) as exc_info:
        await fetch_tmdb_movie(_TMDB_ID, client=mock_client)

    assert exc_info.value.code == TmdbBridgeErrorCode.TIMEOUT_ERROR


@pytest.mark.asyncio
async def test_fetch_tmdb_movie_500_raises_fetch_failed() -> None:
    """HTTP 500 → TmdbBridgeClientError with FETCH_FAILED."""
    mock_response = Mock()
    mock_response.status_code = 500
    error = httpx.HTTPStatusError("server error", request=Mock(), response=mock_response)
    mock_response.raise_for_status = Mock(side_effect=error)

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(TmdbBridgeClientError) as exc_info:
        await fetch_tmdb_movie(_TMDB_ID, client=mock_client)

    assert exc_info.value.code == TmdbBridgeErrorCode.FETCH_FAILED


@pytest.mark.asyncio
async def test_fetch_tmdb_movie_429_raises_rate_limit() -> None:
    """HTTP 429 → TmdbBridgeClientError with RATE_LIMIT_ERROR."""
    mock_response = Mock()
    mock_response.status_code = 429
    error = httpx.HTTPStatusError("rate limited", request=Mock(), response=mock_response)
    mock_response.raise_for_status = Mock(side_effect=error)

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(TmdbBridgeClientError) as exc_info:
        await fetch_tmdb_movie(_TMDB_ID, client=mock_client)

    assert exc_info.value.code == TmdbBridgeErrorCode.RATE_LIMIT_ERROR
