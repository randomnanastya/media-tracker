from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.logging import logger


def handle_client_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError as e:
            logger.error("Network error in client: %s", e)
            raise ValueError(f"Client network error: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error("API status error: %s", e.response.status_code)
            raise ValueError(f"API error: {e.response.text}") from e
        except ValidationError as e:
            logger.error("Validation error: %s", str(e))
            raise HTTPException(status_code=422, detail=str(e.errors())) from e
        except Exception:
            logger.exception("Unexpected client error")
            raise

    return wrapper
