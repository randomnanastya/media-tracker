import os
from typing import Any, cast

import httpx

from app.client.endpoints import SONARR_SERIES
from app.client.error_handler import handle_client_errors
from app.config import logger

SONARR_URL = os.getenv("SONARR_URL")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")


@handle_client_errors
async def fetch_sonarr_series() -> list[dict[str, Any]]:
    """Fetches the list of series from the Sonarr API."""
    api_key = SONARR_API_KEY
    if api_key is None:
        raise ValueError("SONARR_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SONARR_URL}{SONARR_SERIES}",
                headers={"X-Api-Key": api_key},
                timeout=30.0,
            )

            response.raise_for_status()
            series = response.json()
            logger.info("Fetched %d series from Sonarr", len(series))
            return cast(list[dict[str, Any]], series)

        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Sonarr API: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sonarr API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise
        except Exception as e:
            logger.error("Unexpected error while fetching series from Sonarr: %s", e)
            raise


@handle_client_errors
async def fetch_sonarr_episodes(series_id: int) -> list[dict[str, Any]]:
    """Fetches all episodes for a given series from Sonarr API."""
    api_key = SONARR_API_KEY
    if api_key is None:
        raise ValueError("SONARR_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        try:
            url = f"{SONARR_URL}/api/v3/episode?seriesId={series_id}"
            response = await client.get(url, headers={"X-Api-Key": api_key}, timeout=30.0)
            response.raise_for_status()
            episodes = response.json()
            logger.info("Fetched %d episodes for series %d", len(episodes), series_id)
            return cast(list[dict[str, Any]], episodes)
        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Sonarr episodes API: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sonarr episodes API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise
        except Exception as e:
            logger.error("Unexpected error while fetching episodes from Sonarr: %s", e)
            raise
