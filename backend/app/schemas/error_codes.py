from enum import Enum


class ErrorCode(str, Enum):
    """Base error codes shared across services."""

    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class SonarrErrorCode(str, Enum):
    """Sonarr-specific error codes."""

    FETCH_FAILED = "SONARR_FETCH_FAILED"
    INVALID_DATE = "SONARR_INVALID_DATE"

    # Reference shared error codes with a prefix
    NETWORK_ERROR = f"SONARR_{ErrorCode.NETWORK_ERROR}"
    DATABASE_ERROR = f"SONARR_{ErrorCode.DATABASE_ERROR}"
    INTERNAL_ERROR = f"SONARR_{ErrorCode.INTERNAL_ERROR}"
    TIMEOUT_ERROR = f"SONARR_{ErrorCode.TIMEOUT_ERROR}"
    RATE_LIMIT_ERROR = f"SONARR_{ErrorCode.RATE_LIMIT_ERROR}"


class RadarrErrorCode(str, Enum):
    """Radarr-specific error codes."""

    FETCH_FAILED = "RADARR_FETCH_FAILED"
    EXTERNAL_API_ERROR = "RADARR_EXTERNAL_API_ERROR"

    # Reference shared error codes with a prefix
    NETWORK_ERROR = f"RADARR_{ErrorCode.NETWORK_ERROR}"
    DATABASE_ERROR = f"RADARR_{ErrorCode.DATABASE_ERROR}"
    INTERNAL_ERROR = f"RADARR_{ErrorCode.INTERNAL_ERROR}"
    TIMEOUT_ERROR = f"SONARR_{ErrorCode.TIMEOUT_ERROR}"
    RATE_LIMIT_ERROR = f"SONARR_{ErrorCode.RATE_LIMIT_ERROR}"


class JellyfinErrorCode(str, Enum):
    """Jellyfin-specific error codes."""

    FETCH_FAILED = "JELLYFIN_FETCH_FAILED"
    SYNC_FAILED = "JELLYFIN_SYNC_FAILED"

    # Reference shared error codes with a prefix
    NETWORK_ERROR = f"JELLYFIN_{ErrorCode.NETWORK_ERROR}"
    DATABASE_ERROR = f"JELLYFIN_{ErrorCode.DATABASE_ERROR}"
    INTERNAL_ERROR = f"JELLYFIN_{ErrorCode.INTERNAL_ERROR}"
    TIMEOUT_ERROR = f"SONARR_{ErrorCode.TIMEOUT_ERROR}"
    RATE_LIMIT_ERROR = f"SONARR_{ErrorCode.RATE_LIMIT_ERROR}"
