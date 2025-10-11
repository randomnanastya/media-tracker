import os
import logging
import httpx

from app.client.endpoints import RADARR_MOVIES

logger = logging.getLogger(__name__)

RADARR_URL = os.getenv("RADARR_URL")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")


async def fetch_radarr_movies() -> list[dict]:
    """Fetches the list of movies from the Radarr API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{RADARR_URL}{RADARR_MOVIES}",
                headers={"X-Api-Key": RADARR_API_KEY},
                timeout=30.0  # optional timeout
            )
            response.raise_for_status()
            movies = response.json()
            logger.info("Fetched %d movies from Radarr", len(movies))
            return movies
        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Radarr API: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Radarr API returned an unsuccessful status code %s for URL %s",
                e.response.status_code, e.request.url
            )
            raise
        except Exception as e:
            logger.error("Unexpected error while fetching movies from Radarr: %s", e)
            raise

