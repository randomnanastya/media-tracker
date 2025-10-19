from enum import Enum


class SonarrErrorCode(str, Enum):
    SONARR_FETCH_FAILED = "SONARR_FETCH_FAILED"
    INVALID_DATE = "INVALID_DATE"


class RadarrErrorCode(str, Enum):
    RADARR_FETCH_FAILED = "RADARR_FETCH_FAILED"
