import os
from typing import Any, cast

import httpx

from app.client.endpoints import SONARR_SERIES
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import SonarrErrorCode

SONARR_URL = os.getenv("SONARR_URL")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")


class SonarrClientError(ClientError):
    """Custom exception for Sonarr client errors."""

    def __init__(self, code: SonarrErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


async def fetch_sonarr_series() -> list[dict[str, Any]]:
    """Fetches the list of series from the Sonarr API."""
    if SONARR_API_KEY is None:
        logger.error("SONARR_API_KEY is not set")
        raise SonarrClientError(
            code=SonarrErrorCode.INTERNAL_ERROR,
            message="Sonarr API key is not configured",
        )

    if SONARR_URL is None:
        logger.error("SONARR_URL is not set")
        raise SonarrClientError(
            code=SonarrErrorCode.INTERNAL_ERROR,
            message="Sonarr URL is not configured",
        )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SONARR_URL}{SONARR_SERIES}",
                headers={"X-Api-Key": SONARR_API_KEY},
                timeout=30.0,
            )

            response.raise_for_status()
            series = response.json()
            logger.info("Fetched %d series from Sonarr", len(series))
            return cast(list[dict[str, Any]], series)

        except httpx.RequestError as e:
            logger.error("Network error while requesting Sonarr API: %s", e)
            raise SonarrClientError(
                code=SonarrErrorCode.NETWORK_ERROR,
                message="Failed to connect to Sonarr",
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(
                "Sonarr API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise SonarrClientError(
                code=SonarrErrorCode.FETCH_FAILED,
                message=f"Sonarr API error: {e.response.text}",
            ) from e

        except Exception as e:
            logger.error("Unexpected error while fetching series from Sonarr: %s", e)
            raise SonarrClientError(
                code=SonarrErrorCode.INTERNAL_ERROR,
                message="Unexpected error occurred while fetching series",
            ) from e


async def fetch_sonarr_episodes(series_id: int) -> list[dict[str, Any]]:
    """Fetches all episodes for a given series from Sonarr API."""
    if SONARR_API_KEY is None:
        logger.error("SONARR_API_KEY is not set")
        raise SonarrClientError(
            code=SonarrErrorCode.INTERNAL_ERROR,
            message="Sonarr API key is not configured",
        )

    if SONARR_URL is None:
        logger.error("SONARR_URL is not set")
        raise SonarrClientError(
            code=SonarrErrorCode.INTERNAL_ERROR,
            message="Sonarr URL is not configured",
        )

    async with httpx.AsyncClient() as client:
        try:
            url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}"
            response = await client.get(url, headers={"X-Api-Key": SONARR_API_KEY}, timeout=30.0)
            response.raise_for_status()
            episodes = response.json()
            logger.info("Fetched %d episodes for series %d", len(episodes), series_id)
            return cast(list[dict[str, Any]], episodes)
        except httpx.RequestError as e:
            logger.error("Network error while requesting Sonarr episodes API: %s", e)
            raise SonarrClientError(
                code=SonarrErrorCode.NETWORK_ERROR,
                message="Failed to connect to Sonarr",
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sonarr episodes API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise SonarrClientError(
                code=SonarrErrorCode.FETCH_FAILED,
                message=f"Sonarr API error: {e.response.text}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error while fetching episodes from Sonarr: %s", e)
            raise SonarrClientError(
                code=SonarrErrorCode.INTERNAL_ERROR,
                message="Unexpected error occurred while fetching episodes",
            ) from e
