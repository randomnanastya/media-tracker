from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import logger


def handle_api_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to wrap API endpoints and handle exceptions consistently.
    Logs errors and returns meaningful HTTP responses.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)

        except httpx.RequestError as e:
            # Network errors
            logger.exception("Network error during API call: %s", e)
            raise HTTPException(
                status_code=502, detail=f"Network error during API call: {e!s}"
            ) from e
        except SQLAlchemyError as e:
            logger.error("Database error in %s: %s", func.__name__, str(e))

            raise HTTPException(status_code=500, detail="Database operation failed") from e
        except httpx.HTTPStatusError as e:
            # External API returned an error status
            logger.exception(
                "External API returned status %s for URL %s", e.response.status_code, e.request.url
            )
            raise HTTPException(
                status_code=e.response.status_code, detail=f"External API error: {e.response.text}"
            ) from e

        except HTTPException as e:
            if e.status_code == 500:
                logger.exception("Internal server error in API endpoint: %s", e.detail)

                raise HTTPException(
                    status_code=500, detail=f"Internal server error: {e.detail}"
                ) from e

            raise

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception("Unexpected error in API endpoint")
            raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}") from e

    return wrapper
