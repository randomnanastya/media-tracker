"""Sonarr API client (refactored)."""

import os
from typing import Any

import httpx

from app.client.endpoints import SONARR_SERIES
from app.client.pagination import fetch_paginated_simple
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import SonarrErrorCode
from app.utils.config_validator import validate_config


def _get_sonarr_url() -> str | None:
    return os.getenv("SONARR_URL")


def _get_sonarr_api_key() -> str | None:
    return os.getenv("SONARR_API_KEY")


class SonarrClientError(ClientError):
    """Custom exception for Sonarr client errors."""

    def __init__(self, code: SonarrErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


def _get_headers() -> dict[str, str]:
    api_key = _get_sonarr_api_key()
    assert api_key is not None
    return {"X-Api-Key": api_key}


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


@validate_config(
    "SONARR_URL",
    "SONARR_API_KEY",
    error_class=SonarrClientError,
    error_code=SonarrErrorCode.INTERNAL_ERROR,
)
async def fetch_sonarr_series() -> list[dict[str, Any]]:
    """Fetch the list of series from the Sonarr API."""
    url = _get_sonarr_url()
    assert url is not None

    async with httpx.AsyncClient() as client:
        try:
            series = await fetch_paginated_simple(
                client=client,
                url=f"{url}{SONARR_SERIES}",
                headers=_get_headers(),
                timeout=30.0,
                service_name="Sonarr Series",
            )
            return series
        except Exception as e:
            await _handle_sonarr_error(e)
            raise


@validate_config(
    "SONARR_URL",
    "SONARR_API_KEY",
    error_class=SonarrClientError,
    error_code=SonarrErrorCode.INTERNAL_ERROR,
)
async def fetch_sonarr_episodes(series_id: int) -> list[dict[str, Any]]:
    """Fetch all episodes for a given series from Sonarr API."""
    url = _get_sonarr_url()

    async with httpx.AsyncClient() as client:
        try:
            url = f"{url}/api/v3/episode?seriesId={series_id}"
            episodes = await fetch_paginated_simple(
                client=client,
                url=url,
                headers=_get_headers(),
                timeout=30.0,
                service_name=f"Sonarr Episodes (series_id={series_id})",
            )
            return episodes
        except Exception as e:
            await _handle_sonarr_error(e)
            raise
