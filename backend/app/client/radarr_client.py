import os
from typing import Any, cast

import httpx

from app.client.endpoints import RADARR_MOVIES
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import RadarrErrorCode

RADARR_URL = os.getenv("RADARR_URL")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")


class RadarrClientError(ClientError):
    """Custom exception for Radarr client errors."""

    def __init__(self, code: RadarrErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code=code, message=message)


async def fetch_radarr_movies() -> list[dict[str, Any]]:
    """Fetches the list of movies from the Radarr API."""
    if RADARR_API_KEY is None:
        logger.error("RADARR_API_KEY is not set")
        raise RadarrClientError(
            code=RadarrErrorCode.INTERNAL_ERROR,
            message="Radarr API key is not configured",
        )
    if RADARR_URL is None:
        logger.error("RADARR_URL is not set")
        raise RadarrClientError(
            code=RadarrErrorCode.INTERNAL_ERROR,
            message="Radarr URL is not configured",
        )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{RADARR_URL}{RADARR_MOVIES}",
                headers={"X-Api-Key": RADARR_API_KEY},
                timeout=30.0,
            )
            response.raise_for_status()
            movies = response.json()
            logger.info("Fetched %d movies from Radarr", len(movies))
            return cast(list[dict[str, Any]], movies)
        except httpx.RequestError as e:
            logger.error("Network error while requesting Radarr API: %s", e)
            raise RadarrClientError(
                code=RadarrErrorCode.NETWORK_ERROR,
                message="Failed to connect to Radarr",
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Radarr API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise RadarrClientError(
                code=RadarrErrorCode.EXTERNAL_API_ERROR,
                message=f"Radarr API error: {e.response.text}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error while fetching movies from Radarr: %s", e)
            raise RadarrClientError(
                code=RadarrErrorCode.INTERNAL_ERROR,
                message="Unexpected error occurred while fetching movies",
            ) from e
