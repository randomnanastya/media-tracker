"""Base HTTP client with common functionality."""

from typing import Any

import httpx

from app.config import logger
from app.exceptions.client_errors import ClientError


class BaseHTTPClient:
    """
    Base HTTP client with common error handling and logging.

    Provides:
    - Standardized error handling for httpx requests
    - Logging for requests and responses
    - Type-safe JSON responses
    """

    def __init__(self, base_url: str, api_key: str, service_name: str):
        """
        Initialize base HTTP client.

        Args:
            base_url: Base URL for the service
            api_key: API key for authentication
            service_name: Name of the service (for logging/errors)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.service_name = service_name

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for requests.

        Override this method in subclasses for service-specific headers.

        Returns:
            Dictionary of headers
        """
        return {"X-Api-Key": self.api_key}

    async def _handle_request_error(
        self,
        error: Exception,
        error_code: Any,
        error_class: type[ClientError],
    ) -> None:
        """
        Handle request errors uniformly.

        Args:
            error: The exception that occurred
            error_code: Error code enum value
            error_class: ClientError subclass to raise

        Raises:
            error_class: With appropriate message
        """
        if isinstance(error, httpx.RequestError):
            logger.error(
                "Network error while requesting %s API: %s",
                self.service_name,
                error,
            )
            raise error_class(
                code=error_code.NETWORK_ERROR,
                message=f"Failed to connect to {self.service_name}",
            ) from error

        elif isinstance(error, httpx.HTTPStatusError):
            logger.error(
                "%s API returned status %s for URL %s",
                self.service_name,
                error.response.status_code,
                error.request.url,
            )
            raise error_class(
                code=error_code.FETCH_FAILED,
                message=f"{self.service_name} API error: {error.response.text}",
            ) from error

        else:
            logger.error(
                "Unexpected error while fetching from %s: %s",
                self.service_name,
                error,
            )
            raise error_class(
                code=error_code.INTERNAL_ERROR,
                message=f"Unexpected error occurred while fetching from {self.service_name}",
            ) from error

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Perform GET request.

        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response as Python object

        Raises:
            ClientError: On request failure
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params or {},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
