import os
from typing import Any, cast

import httpx

from app.client.endpoints import RADARR_MOVIES
from app.core.logging import logger

RADARR_URL = os.getenv("RADARR_URL")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")


async def fetch_radarr_movies() -> list[dict[str, Any]]:
    """Fetches the list of movies from the Radarr API."""
    api_key = RADARR_API_KEY
    if api_key is None:
        raise ValueError("RADARR_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{RADARR_URL}{RADARR_MOVIES}",
                headers={"X-Api-Key": api_key},
                timeout=30.0,
            )
            response.raise_for_status()
            movies = response.json()
            logger.info("Fetched %d movies from Radarr", len(movies))
            return cast(list[dict[str, Any]], movies)
        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Radarr API: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Radarr API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise
        except Exception as e:
            logger.error("Unexpected error while fetching movies from Radarr: %s", e)
            raise
