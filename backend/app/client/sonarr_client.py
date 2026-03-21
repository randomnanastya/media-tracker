"""Sonarr API client (refactored)."""

from typing import Any

import httpx

from app.client.endpoints import SONARR_SERIES
from app.client.pagination import fetch_paginated_simple
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import SonarrErrorCode


class SonarrClientError(ClientError):
    """Custom exception for Sonarr client errors."""

    def __init__(self, code: SonarrErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


async def _handle_sonarr_error(error: Exception) -> None:
    """Handle Sonarr API errors uniformly."""
    if isinstance(error, httpx.RequestError):
        logger.error("Network error while requesting Sonarr API: %s", error)
        raise SonarrClientError(
            code=SonarrErrorCode.NETWORK_ERROR,
            message="Failed to connect to Sonarr",
        ) from error

    elif isinstance(error, httpx.HTTPStatusError):
        logger.error(
            "Sonarr API returned status %s for URL %s",
            error.response.status_code,
            error.request.url,
        )
        raise SonarrClientError(
            code=SonarrErrorCode.FETCH_FAILED,
            message=f"Sonarr API error: {error.response.text}",
        ) from error

    else:
        logger.error("Unexpected error while fetching from Sonarr: %s", error)
        raise SonarrClientError(
            code=SonarrErrorCode.INTERNAL_ERROR,
            message="Unexpected error occurred while fetching from Sonarr",
        ) from error


async def fetch_sonarr_series(url: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch the list of series from the Sonarr API."""
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient() as client:
        try:
            series = await fetch_paginated_simple(
                client=client,
                url=f"{url}{SONARR_SERIES}",
                headers=headers,
                timeout=30.0,
                service_name="Sonarr Series",
            )
            return series
        except Exception as e:
            await _handle_sonarr_error(e)
            raise


async def fetch_sonarr_episodes(url: str, api_key: str, series_id: int) -> list[dict[str, Any]]:
    """Fetch all episodes for a given series from Sonarr API."""
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient() as client:
        try:
            episode_url = f"{url}/api/v3/episode?seriesId={series_id}"
            episodes = await fetch_paginated_simple(
                client=client,
                url=episode_url,
                headers=headers,
                timeout=30.0,
                service_name=f"Sonarr Episodes (series_id={series_id})",
            )
            return episodes
        except Exception as e:
            await _handle_sonarr_error(e)
            raise
