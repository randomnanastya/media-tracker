"""TMDB Bridge API client (public, no auth)."""

from typing import Any

import httpx

from app.client.endpoints import TMDB_BRIDGE_MOVIE
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import TmdbBridgeErrorCode

BRIDGE_BASE_URL = "https://bridge.mediatrackr.org"


class TmdbBridgeClientError(ClientError):
    def __init__(self, code: TmdbBridgeErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


async def fetch_tmdb_movie(
    tmdb_id: str,
    *,
    client: httpx.AsyncClient,
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    """Fetch movie metadata from Bridge.

    Returns:
        dict on 200; None on 404 (movie not in TMDB — skip silently).

    Raises:
        TmdbBridgeClientError: on network/timeout/HTTP errors.
    """
    url = f"{BRIDGE_BASE_URL}{TMDB_BRIDGE_MOVIE.format(tmdb_id=tmdb_id)}"
    try:
        response = await client.get(url, timeout=timeout)
        if response.status_code == 404:
            logger.info("TMDB Bridge: movie tmdb_id=%s not found", tmdb_id)
            return None
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data
    except httpx.TimeoutException as e:
        logger.warning("TMDB Bridge timeout for tmdb_id=%s: %s", tmdb_id, e)
        raise TmdbBridgeClientError(
            code=TmdbBridgeErrorCode.TIMEOUT_ERROR,
            message=f"Bridge timeout for tmdb_id={tmdb_id}",
        ) from e
    except httpx.RequestError as e:
        logger.warning("TMDB Bridge network error for tmdb_id=%s: %s", tmdb_id, e)
        raise TmdbBridgeClientError(
            code=TmdbBridgeErrorCode.NETWORK_ERROR,
            message=f"Bridge unreachable for tmdb_id={tmdb_id}",
        ) from e
    except httpx.HTTPStatusError as e:
        logger.warning(
            "TMDB Bridge HTTP %s for tmdb_id=%s",
            e.response.status_code,
            tmdb_id,
        )
        code = (
            TmdbBridgeErrorCode.RATE_LIMIT_ERROR
            if e.response.status_code == 429
            else TmdbBridgeErrorCode.FETCH_FAILED
        )
        raise TmdbBridgeClientError(
            code=code,
            message=f"Bridge HTTP {e.response.status_code} for tmdb_id={tmdb_id}",
        ) from e
