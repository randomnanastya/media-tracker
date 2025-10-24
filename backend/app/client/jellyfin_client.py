import os
from typing import Any, cast

import httpx

from app.client.endpoints import JELLYFIN_USERS
from app.client.error_handler import handle_client_errors
from app.config import logger

JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")


@handle_client_errors
async def fetch_jellyfin_users() -> list[dict[str, Any]]:
    """Fetches all users from Jellyfin."""
    if JELLYFIN_API_KEY is None:
        raise ValueError("JELLYFIN_API_KEY is not set")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url=f"{JELLYFIN_URL}{JELLYFIN_USERS}",
            headers={"X-Emby-Token": JELLYFIN_API_KEY},
            timeout=30.0,
        )
        response.raise_for_status()
        users = response.json()
        logger.info("Fetched %d users from Jellyfin", len(users))
        return cast(list[dict[str, Any]], users)


@handle_client_errors
async def fetch_jellyfin_movies_for_user(jellyfin_user_id: str) -> list[dict[str, Any]]:
    """Fetches ALL movies for a user from Jellyfin with pagination."""
    if JELLYFIN_API_KEY is None:
        raise ValueError("JELLYFIN_API_KEY is not set")

    base_url = f"{JELLYFIN_URL}/Users/{jellyfin_user_id}/Items"
    params = {
        "IncludeItemTypes": "Movie",
        "Recursive": "true",
        "Fields": "ProviderIds,UserData",
        "ImageTypeLimit": 0,
    }

    all_items: list[dict[str, Any]] = []
    start_index = 0
    limit = 100

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                url=base_url,
                headers={"X-Emby-Token": JELLYFIN_API_KEY},
                params={**params, "StartIndex": start_index, "Limit": limit},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("Items", [])
            all_items.extend(items)

            total = data.get("TotalRecordCount", 0)
            fetched = len(all_items)

            if fetched >= total or len(items) < limit:
                break

            start_index += limit
            logger.debug("Fetched %d/%d movies for user %s", fetched, total, jellyfin_user_id)

    logger.info("Fetched %d movies for Jellyfin user %s", len(all_items), jellyfin_user_id)
    return cast(list[dict[str, Any]], all_items)
