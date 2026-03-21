"""Radarr API client (refactored)."""

from typing import Any

import httpx

from app.client.endpoints import RADARR_MOVIES
from app.client.pagination import fetch_paginated_simple
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import RadarrErrorCode


class RadarrClientError(ClientError):
    """Custom exception for Radarr client errors."""

    def __init__(self, code: RadarrErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


async def _handle_radarr_error(error: Exception) -> None:
    """Handle Radarr API errors uniformly."""
    if isinstance(error, httpx.RequestError):
        logger.error("Network error while requesting Radarr API: %s", error)
        raise RadarrClientError(
            code=RadarrErrorCode.NETWORK_ERROR,
            message="Failed to connect to Radarr",
        ) from error

    elif isinstance(error, httpx.HTTPStatusError):
        logger.error(
            "Radarr API returned status %s for URL %s",
            error.response.status_code,
            error.request.url,
        )
        raise RadarrClientError(
            code=RadarrErrorCode.EXTERNAL_API_ERROR,
            message=f"Radarr API error: {error.response.text}",
        ) from error

    else:
        logger.error("Unexpected error while fetching from Radarr: %s", error)
        raise RadarrClientError(
            code=RadarrErrorCode.INTERNAL_ERROR,
            message="Unexpected error occurred while fetching movies",
        ) from error


async def fetch_radarr_movies(url: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch the list of movies from the Radarr API."""
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient() as client:
        try:
            movies = await fetch_paginated_simple(
                client=client,
                url=f"{url}{RADARR_MOVIES}",
                headers=headers,
                timeout=30.0,
                service_name="Radarr",
            )
            return movies
        except Exception as e:
            await _handle_radarr_error(e)
            raise  # Never reached, but makes mypy happy
