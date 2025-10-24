from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx

from app.config import logger


def handle_client_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError as e:
            logger.error("Network error in client: %s", e)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP %s error in %s: %s",
                e.response.status_code,
                func.__name__,
                e.response.text[:500],
            )
            raise
        except Exception:
            logger.exception("Unexpected error in %s", func.__name__)
            raise

    return wrapper
