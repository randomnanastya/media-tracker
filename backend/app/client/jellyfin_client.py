"""Jellyfin API client (refactored)."""

import os
from typing import Any

import httpx

from app.client.endpoints import JELLYFIN_USERS
from app.client.pagination import fetch_paginated, fetch_paginated_simple
from app.config import logger
from app.exceptions.client_errors import ClientError
from app.schemas.error_codes import JellyfinErrorCode
from app.utils.config_validator import validate_config


def _get_jellyfin_url() -> str | None:
    return os.getenv("JELLYFIN_URL")


def _get_jellyfin_api_key() -> str | None:
    return os.getenv("JELLYFIN_API_KEY")


class JellyfinClientError(ClientError):
    """Custom exception for Jellyfin client errors."""

    def __init__(self, code: JellyfinErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(code, message)


def _get_headers() -> dict[str, str]:
    """Get Jellyfin request headers."""
    api_key = _get_jellyfin_api_key()
    assert api_key is not None
    return {"X-Emby-Token": api_key}


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


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_users() -> list[dict[str, Any]]:
    """Fetch all users from Jellyfin."""
    url = _get_jellyfin_url()
    assert url is not None

    async with httpx.AsyncClient() as client:
        try:
            users = await fetch_paginated_simple(
                client=client,
                url=f"{url}{JELLYFIN_USERS}",
                headers=_get_headers(),
                service_name="Jellyfin Users",
            )
            return users
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise  # Never reached, but makes mypy happy


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_movies() -> list[dict[str, Any]]:
    """Fetch ALL movies from Jellyfin with pagination."""
    url = _get_jellyfin_url()
    api_key = _get_jellyfin_api_key()
    assert url is not None
    assert api_key is not None

    base_url = f"{url}/Items/?api_key={api_key}"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
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


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_series() -> list[dict[str, Any]]:
    """Fetch ALL series from Jellyfin with pagination."""
    url = _get_jellyfin_url()
    api_key = _get_jellyfin_api_key()
    assert api_key is not None
    assert url is not None

    base_url = f"{url}/Items/?api_key={api_key}"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
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


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_seasons(series_id: str) -> list[dict[str, Any]]:
    """Fetch ALL seasons by series from Jellyfin."""
    url = _get_jellyfin_url()
    assert url is not None

    base_url = f"{url}/Shows/{series_id}/Seasons"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
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


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_episodes(series_id: str) -> list[dict[str, Any]]:
    """Fetch ALL episodes by series from Jellyfin."""
    url = _get_jellyfin_url()
    assert url is not None

    base_url = f"{url}/Shows/{series_id}/Episodes"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
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


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_movies_for_user_all(jellyfin_user_id: str) -> list[dict[str, Any]]:
    """Fetch ALL movies for a user from Jellyfin (both watched and unwatched)."""
    url = _get_jellyfin_url()
    assert url is not None

    base_url = f"{url}/Users/{jellyfin_user_id}/Items"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
                params={
                    "IncludeItemTypes": "Movie",
                    "Recursive": "true",
                    "Fields": "ProviderIds,UserData",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name=f"Jellyfin Movies for User {jellyfin_user_id}",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise


@validate_config(
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    error_class=JellyfinClientError,
    error_code=JellyfinErrorCode.INTERNAL_ERROR,
)
async def fetch_jellyfin_episodes_for_user_all(jellyfin_user_id: str) -> list[dict[str, Any]]:
    """Fetch ALL episodes for a user from Jellyfin (both watched and unwatched)."""
    url = _get_jellyfin_url()
    assert url is not None

    base_url = f"{url}/Users/{jellyfin_user_id}/Items"

    async with httpx.AsyncClient() as client:
        try:
            items = await fetch_paginated(
                client=client,
                url=base_url,
                headers=_get_headers(),
                params={
                    "IncludeItemTypes": "Episode",
                    "Recursive": "true",
                    "Fields": "UserData",
                    "ImageTypeLimit": "0",
                },
                limit=100,
                timeout=60.0,
                service_name=f"Jellyfin Episodes for User {jellyfin_user_id}",
            )
            return items
        except Exception as e:
            await _handle_jellyfin_error(e)
            raise
