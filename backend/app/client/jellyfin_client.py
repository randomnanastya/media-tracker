"""Jellyfin API client (refactored)."""

from typing import Any

import httpx

from app.client.endpoints import JELLYFIN_USERS
from app.client.pagination import fetch_paginated, fetch_paginated_simple
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import JellyfinErrorCode


class JellyfinClientError(ClientError):
    """Custom exception for Jellyfin client errors."""

    def __init__(self, code: JellyfinErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code, message)


async def _handle_jellyfin_error(error: Exception) -> None:
    """Handle Jellyfin API errors uniformly."""
    if isinstance(error, httpx.RequestError):
        logger.error("Network error while requesting Jellyfin API: %s", error)
        raise JellyfinClientError(
            code=JellyfinErrorCode.NETWORK_ERROR,
            message="Failed to connect to Jellyfin",
        ) from error

    elif isinstance(error, httpx.HTTPStatusError):
        logger.error(
            "Jellyfin API returned status %s for URL %s",
            error.response.status_code,
            error.request.url,
        )
        raise JellyfinClientError(
            code=JellyfinErrorCode.FETCH_FAILED,
            message=f"Jellyfin API error: {error.response.text}",
        ) from error

    else:
        logger.error("Unexpected error while fetching from Jellyfin: %s", error)
        raise JellyfinClientError(
            code=JellyfinErrorCode.INTERNAL_ERROR,
            message="Unexpected error occurred while fetching from Jellyfin",
        ) from error


async def fetch_jellyfin_users(url: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch all users from Jellyfin."""
    headers = {"X-Emby-Token": api_key}

    async with httpx.AsyncClient() as client:
        try:
            users = await fetch_paginated_simple(
                client=client,
                url=f"{url}{JELLYFIN_USERS}",
                headers=headers,
                service_name="Jellyfin Users",
            )
            return users
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise  # Never reached, but makes mypy happy


async def fetch_jellyfin_movies(url: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch ALL movies from Jellyfin with pagination."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Items/?api_key={api_key}"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "IncludeItemTypes": "Movie",
                    "Recursive": "true",
                    "Fields": "ProviderIds",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name="Jellyfin Movies",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


async def fetch_jellyfin_series(url: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch ALL series from Jellyfin with pagination."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Items/?api_key={api_key}"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "IncludeItemTypes": "Series",
                    "Recursive": "true",
                    "Fields": "ProviderIds",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name="Jellyfin Series",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


async def fetch_jellyfin_seasons(
    url: str, api_key: str, series_jellyfin_id: str
) -> list[dict[str, Any]]:
    """Fetch ALL seasons by series from Jellyfin."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Shows/{series_jellyfin_id}/Seasons"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name="Jellyfin Seasons",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


async def fetch_jellyfin_episodes(
    url: str, api_key: str, series_jellyfin_id: str
) -> list[dict[str, Any]]:
    """Fetch ALL episodes by series from Jellyfin."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Shows/{series_jellyfin_id}/Episodes"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name="Jellyfin Episodes",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


async def fetch_jellyfin_movies_for_user_all(
    url: str, api_key: str, user_jellyfin_id: str
) -> list[dict[str, Any]]:
    """Fetch ALL movies for a user from Jellyfin (both watched and unwatched)."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Users/{user_jellyfin_id}/Items"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "IncludeItemTypes": "Movie",
                    "Recursive": "true",
                    "Fields": "ProviderIds,UserData",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name=f"Jellyfin Movies for User {user_jellyfin_id}",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


async def fetch_jellyfin_episodes_for_user_all(
    url: str, api_key: str, user_jellyfin_id: str
) -> list[dict[str, Any]]:
    """Fetch ALL episodes for a user from Jellyfin (both watched and unwatched)."""
    headers = {"X-Emby-Token": api_key}
    base_url = f"{url}/Users/{user_jellyfin_id}/Items"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=headers,
                params={
                    "IncludeItemTypes": "Episode",
                    "Recursive": "true",
                    "Fields": "UserData",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name=f"Jellyfin Episodes for User {user_jellyfin_id}",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise
