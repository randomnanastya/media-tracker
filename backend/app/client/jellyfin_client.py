import os
from typing import Any, cast

import httpx

from app.client.endpoints import JELLYFIN_USERS
from app.client.error_handler import handle_client_errors
from app.core.logging import logger

JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")


@handle_client_errors
async def fetch_jellyfin_users() -> list[dict[str, Any]]:
    """Fetches the list of movies from the Radarr API."""

    api_key = JELLYFIN_API_KEY
    if api_key is None:
        raise ValueError("JELLYFIN_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url=f"{JELLYFIN_URL}{JELLYFIN_USERS}",
                headers={"X-Emby-Token": api_key},
                timeout=30.0,
            )

            response.raise_for_status()
            users = response.json()
            logger.info("Fetched %d jellyfin users from Jellyfin", len(users))
            return cast(list[dict[str, Any]], users)
        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Jellyfin API: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "Jellyfin API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise
        except Exception as e:
            logger.error("Unexpected error while fetching users from Jellyfin: %s", e)
            raise
