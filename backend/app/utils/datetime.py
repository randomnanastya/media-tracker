from datetime import UTC, datetime


def parse_datetime(datetime_str: str | None) -> datetime | None:
    """Parse datetime string from Jellyfin/other sources."""
    if not datetime_str:
        return None

    try:
        # Jellyfin format: "2025-09-01T12:38:08.9937847Z"
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None
