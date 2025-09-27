import logging
from functools import wraps
from fastapi import HTTPException

import httpx

logger = logging.getLogger(__name__)

def handle_api_errors(func):
    """
    Decorator to wrap API endpoints and handle exceptions consistently.
    Logs errors and returns meaningful HTTP responses.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        except httpx.RequestError as e:
            # Network errors
            logger.exception("Network error during API call: %s", e)
            raise HTTPException(
                status_code=502,
                detail=f"Network error during API call: {str(e)}"
            )

        except httpx.HTTPStatusError as e:
            # External API returned an error status
            logger.exception(
                "External API returned status %s for URL %s",
                e.response.status_code, e.request.url
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"External API error: {e.response.text}"
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception("Unexpected error in API endpoint")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    return wrapper
