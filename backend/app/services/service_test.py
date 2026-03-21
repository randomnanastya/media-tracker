"""Service connection test utilities."""

import httpx

from app.models import ServiceType


async def test_service_connection(
    service_type: ServiceType, url: str, api_key: str
) -> tuple[bool, str]:
    """Test connection to an external service. Returns (success, message)."""
    endpoints: dict[ServiceType, tuple[str, dict[str, str]]] = {
        ServiceType.RADARR: (
            f"{url}/api/v3/system/status",
            {"X-Api-Key": api_key},
        ),
        ServiceType.SONARR: (
            f"{url}/api/v3/system/status",
            {"X-Api-Key": api_key},
        ),
        ServiceType.JELLYFIN: (
            f"{url}/System/Info",
            {"X-Emby-Token": api_key},
        ),
    }

    test_url, headers = endpoints[service_type]
    service_name = service_type.value.capitalize()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(test_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return True, f"{service_name} connection successful"
    except httpx.RequestError as e:
        return False, f"Cannot connect to {service_name}: {e}"
    except httpx.HTTPStatusError as e:
        return False, f"{service_name} returned status {e.response.status_code}"
