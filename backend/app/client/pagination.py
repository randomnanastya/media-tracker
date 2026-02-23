"""Pagination utilities for external APIs."""

from typing import Any

import httpx

from app.config import logger


async def fetch_paginated(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    limit: int = 100,
    timeout: float = 60.0,
    item_key: str = "Items",
    total_key: str = "TotalRecordCount",
    start_index_param: str = "StartIndex",
    limit_param: str = "Limit",
    service_name: str = "API",
) -> list[dict[str, Any]]:
    """
    Fetch all items from a paginated API.

    Generic pagination utility that works with Jellyfin-style APIs.

    Args:
        client: httpx AsyncClient instance
        url: API endpoint URL
        headers: Request headers
        params: Base query parameters
        limit: Items per page
        timeout: Request timeout in seconds
        item_key: Key in response containing items list
        total_key: Key in response containing total count
        start_index_param: Query param name for start index
        limit_param: Query param name for limit
        service_name: Service name for logging

    Returns:
        List of all fetched items

    Examples:
        >>> async with httpx.AsyncClient() as client:
        ...     items = await fetch_paginated(
        ...         client=client,
        ...         url="https://api.example.com/items",
        ...         headers={"Authorization": "Bearer token"},
        ...         params={"filter": "movies"},
        ...         service_name="Example API",
        ...     )
    """
    all_items: list[dict[str, Any]] = []
    start_index = 0

    while True:
        # Add pagination params
        current_params = {
            **params,
            start_index_param: start_index,
            limit_param: limit,
        }

        response = await client.get(
            url=url,
            headers=headers,
            params=current_params,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Extract items
        items = data.get(item_key, [])
        all_items.extend(items)

        # Check if we've fetched everything
        total = data.get(total_key, 0)
        fetched = len(all_items)

        logger.debug(
            "Fetched %d/%d items from %s",
            fetched,
            total,
            service_name,
        )

        # Stop if we've fetched all items or received less than requested
        if fetched >= total or len(items) < limit:
            break

        start_index += limit

    logger.info("Fetched %d items from %s", len(all_items), service_name)
    return all_items


async def fetch_paginated_simple(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
    service_name: str = "API",
) -> list[dict[str, Any]]:
    """
    Fetch items from a non-paginated API (returns list directly).

    For APIs that return a simple list without pagination wrapper.

    Args:
        client: httpx AsyncClient instance
        url: API endpoint URL
        headers: Request headers
        params: Query parameters
        timeout: Request timeout in seconds
        service_name: Service name for logging

    Returns:
        List of fetched items

    Examples:
        >>> async with httpx.AsyncClient() as client:
        ...     items = await fetch_paginated_simple(
        ...         client=client,
        ...         url="https://api.example.com/movies",
        ...         headers={"X-Api-Key": "key"},
        ...         service_name="Radarr",
        ...     )
    """
    response = await client.get(
        url=url,
        headers=headers,
        params=params or {},
        timeout=timeout,
    )
    response.raise_for_status()
    items = response.json()

    logger.info("Fetched %d items from %s", len(items), service_name)
    return items  # type: ignore[no-any-return]
