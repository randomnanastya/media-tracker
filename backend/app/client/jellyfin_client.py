import os
from typing import Any, cast

import httpx

from app.client.endpoints import JELLYFIN_USERS
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import JellyfinErrorCode

JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")


class JellyfinClientError(ClientError):
    """Custom exception for Jellyfin client errors."""

    def __init__(self, code: JellyfinErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code, message)


async def fetch_jellyfin_users() -> list[dict[str, Any]]:
    """Fetches all users from Jellyfin."""
    if JELLYFIN_API_KEY is None:
        logger.error("JELLYFIN_API_KEY is not set")
        raise JellyfinClientError(
            code=JellyfinErrorCode.INTERNAL_ERROR,
            message="Jellyfin API key is not configured",
        )
    if JELLYFIN_URL is None:
        logger.error("JELLYFIN_URL is not set")
        raise JellyfinClientError(
            code=JellyfinErrorCode.INTERNAL_ERROR,
            message="Jellyfin URL is not configured",
        )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url=f"{JELLYFIN_URL}{JELLYFIN_USERS}",
                headers={"X-Emby-Token": JELLYFIN_API_KEY},
                timeout=30.0,
            )
            response.raise_for_status()
            users = response.json()
            logger.info("Fetched %d users from Jellyfin", len(users))
            return cast(list[dict[str, Any]], users)
        except httpx.RequestError as e:
            logger.error("Network error while requesting Jellyfin users API: %s", e)
            raise JellyfinClientError(
                code=JellyfinErrorCode.NETWORK_ERROR,
                message="Failed to connect to Jellyfin",
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Jellyfin users API returned an unsuccessful status code %s for URL %s",
                e.response.status_code,
                e.request.url,
            )
            raise JellyfinClientError(
                code=JellyfinErrorCode.FETCH_FAILED,
                message=f"Jellyfin API error: {e.response.text}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error while fetching users from Jellyfin: %s", e)
            raise JellyfinClientError(
                code=JellyfinErrorCode.INTERNAL_ERROR,
                message="Unexpected error occurred while fetching users",
            ) from e


async def fetch_jellyfin_movies_for_user(jellyfin_user_id: str) -> list[dict[str, Any]]:
    """Fetches ALL movies for a user from Jellyfin with pagination."""
    if JELLYFIN_API_KEY is None:
        logger.error("JELLYFIN_API_KEY is not set")
        raise JellyfinClientError(
            code=JellyfinErrorCode.INTERNAL_ERROR,
            message="Jellyfin API key is not configured",
        )
    if JELLYFIN_URL is None:
        logger.error("JELLYFIN_URL is not set")
        raise JellyfinClientError(
            code=JellyfinErrorCode.INTERNAL_ERROR,
            message="Jellyfin URL is not configured",
        )

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
            try:
                current_params = dict(params)
                current_params["StartIndex"] = start_index
                current_params["Limit"] = limit

                response = await client.get(
                    url=base_url,
                    headers={"X-Emby-Token": JELLYFIN_API_KEY},
                    params=current_params,
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
            except httpx.RequestError as e:
                logger.error("Network error while requesting Jellyfin movies API: %s", e)
                raise JellyfinClientError(
                    code=JellyfinErrorCode.NETWORK_ERROR,
                    message="Failed to connect to Jellyfin",
                ) from e
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Jellyfin movies API returned an unsuccessful status code %s for URL %s",
                    e.response.status_code,
                    e.request.url,
                )
                raise JellyfinClientError(
                    code=JellyfinErrorCode.FETCH_FAILED,
                    message=f"Jellyfin API error: {e.response.text}",
                ) from e
            except Exception as e:
                logger.error("Unexpected error while fetching movies from Jellyfin: %s", e)
                raise JellyfinClientError(
                    code=JellyfinErrorCode.INTERNAL_ERROR,
                    message="Unexpected error occurred while fetching movies",
                ) from e

    logger.info("Fetched %d movies for Jellyfin user %s", len(all_items), jellyfin_user_id)
    return all_items
