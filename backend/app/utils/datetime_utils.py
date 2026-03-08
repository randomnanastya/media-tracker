"""Datetime parsing utilities."""

from datetime import UTC, datetime
from typing import Any


def parse_iso_datetime(
    dt_str: str | None,
    context: str = "Unknown",
) -> datetime | None:
    """
    Parse ISO datetime string to UTC datetime.

    Handles:
    - ISO format with Z suffix (2024-01-15T10:30:00Z)
    - ISO format with timezone (+00:00)
    - Naive datetime (assumes UTC)

    Args:
        dt_str: ISO datetime string or None
        context: Context for logging (e.g., movie title, series name)

    Returns:
        UTC datetime or None if parsing fails

    Examples:
        >>> parse_iso_datetime("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)

        >>> parse_iso_datetime("2024-01-15T10:30:00+00:00")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)

        >>> parse_iso_datetime(None)
        None
    """
    if not dt_str:
        return None

    try:
        # Replace Z with +00:00 for proper ISO parsing
        normalized = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)

        # Ensure timezone awareness
        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

        return dt

    except (ValueError, TypeError, AttributeError) as exc:
        from app.config import logger

        logger.warning(
            "Failed to parse datetime '%s' for %s: %s",
            dt_str,
            context,
            exc,
        )
        return None


def parse_date_from_dict(
    data: dict[str, Any],
    key: str,
    context: str = "Unknown",
) -> datetime | None:
    """
    Extract and parse datetime from dictionary.

    Args:
        data: Dictionary containing datetime field
        key: Key to extract datetime from
        context: Context for logging

    Returns:
        Parsed UTC datetime or None

    Examples:
        >>> parse_date_from_dict({"inCinemas": "2024-01-15T10:30:00Z"}, "inCinemas", "Movie Title")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
    """
    dt_str = data.get(key)
    return parse_iso_datetime(dt_str, context=context)
