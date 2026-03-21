"""Configuration validation utilities."""

import os
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from app.config import logger

if TYPE_CHECKING:
    from app.exceptions.client_errors import ClientError

T = TypeVar("T", bound=Callable[..., Any])


def validate_config(
    *required_vars: str,
    error_class: "type[ClientError] | None" = None,
    error_code: Any | None = None,
) -> Callable[[T], T]:
    """
    Decorator to validate required environment variables before function execution.

    Args:
        *required_vars: Names of required environment variables
        error_class: Exception class to raise on validation failure (optional)
        error_code: Error code to pass to error_class (required if error_class is provided)

    Returns:
        Decorated function that validates config before execution

    Examples:
        >>> @validate_config("API_KEY", "API_URL", error_class=SonarrClientError, error_code=SonarrErrorCode.INTERNAL_ERROR)
        ... async def fetch_data():
        ...     pass

    Raises:
        error_class: If validation fails and error_class is provided
    """

    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            missing = [var for var in required_vars if not os.getenv(var)]

            if missing:
                error_msg = _format_config_error(missing[0])
                logger.error(error_msg)

                if error_class:
                    if error_code is None:
                        msg = "error_code must be provided when error_class is specified"
                        raise ValueError(msg)
                    raise error_class(code=error_code, message=error_msg)

                # If no error_class, just log warning and continue
                logger.warning("Proceeding without required config - may fail")

            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _format_config_error(var_name: str) -> str:
    """
    Format a user-friendly error message for missing config variable.

    Args:
        var_name: Name of the missing environment variable

    Returns:
        User-friendly error message

    Examples:
        >>> _format_config_error("SONARR_API_KEY")
        'Sonarr API key is not configured'
        >>> _format_config_error("JELLYFIN_URL")
        'Jellyfin URL is not configured'
    """
    # Extract service name and config type
    parts = var_name.split("_")
    if len(parts) >= 2:
        service = parts[0].capitalize()

        # Handle special cases for config type formatting
        config_parts = parts[1:]
        if config_parts == ["API", "KEY"]:
            config_type = "API key"
        elif config_parts == ["URL"]:
            config_type = "URL"
        else:
            config_type = " ".join(config_parts).lower()

        return f"{service} {config_type} is not configured"

    # Fallback for unexpected format
    return f"{var_name} is not configured"


def get_required_env(var_name: str, default: str | None = None) -> str:
    """
    Get required environment variable or raise error.

    Args:
        var_name: Name of environment variable
        default: Default value if not set (optional)

    Returns:
        Value of environment variable

    Raises:
        ValueError: If variable not set and no default provided

    Examples:
        >>> get_required_env("DATABASE_URL")
        'postgresql://...'

        >>> get_required_env("OPTIONAL_VAR", default="default_value")
        'default_value'
    """
    value = os.getenv(var_name, default)

    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is not set")

    return value
