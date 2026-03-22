"""Constants for sync job scheduling."""

from collections.abc import Awaitable, Callable

from app.models import SchedulePreset, ServiceType, SyncJobType
from app.services.jobs import (
    jellyfin_import_movies_job,
    jellyfin_import_series_job,
    jellyfin_import_users_job,
    jellyfin_sync_movie_watch_history_job,
    jellyfin_sync_series_watch_history_job,
    radarr_import_job,
    sonarr_import_job,
)

JOB_REGISTRY: dict[SyncJobType, tuple[Callable[..., Awaitable[None]], ServiceType]] = {
    SyncJobType.JELLYFIN_USERS_IMPORT: (jellyfin_import_users_job, ServiceType.JELLYFIN),
    SyncJobType.RADARR_IMPORT: (radarr_import_job, ServiceType.RADARR),
    SyncJobType.JELLYFIN_MOVIES_IMPORT: (jellyfin_import_movies_job, ServiceType.JELLYFIN),
    SyncJobType.JELLYFIN_MOVIE_WATCH_HISTORY: (
        jellyfin_sync_movie_watch_history_job,
        ServiceType.JELLYFIN,
    ),
    SyncJobType.SONARR_IMPORT: (sonarr_import_job, ServiceType.SONARR),
    SyncJobType.JELLYFIN_SERIES_IMPORT: (jellyfin_import_series_job, ServiceType.JELLYFIN),
    SyncJobType.JELLYFIN_SERIES_WATCH_HISTORY: (
        jellyfin_sync_series_watch_history_job,
        ServiceType.JELLYFIN,
    ),
}

DEFAULT_SCHEDULES: dict[SyncJobType, str] = {
    SyncJobType.JELLYFIN_USERS_IMPORT: "0 1 1 * *",
    SyncJobType.RADARR_IMPORT: "10 1 * * *",
    SyncJobType.JELLYFIN_MOVIES_IMPORT: "20 1 * * *",
    SyncJobType.JELLYFIN_MOVIE_WATCH_HISTORY: "30 1 * * *",
    SyncJobType.SONARR_IMPORT: "40 1 * * *",
    SyncJobType.JELLYFIN_SERIES_IMPORT: "50 1 * * *",
    SyncJobType.JELLYFIN_SERIES_WATCH_HISTORY: "0 2 * * *",
}

DEFAULT_PRESETS: dict[SyncJobType, SchedulePreset] = {
    SyncJobType.JELLYFIN_USERS_IMPORT: SchedulePreset.MONTHLY,
    SyncJobType.RADARR_IMPORT: SchedulePreset.DAILY,
    SyncJobType.JELLYFIN_MOVIES_IMPORT: SchedulePreset.DAILY,
    SyncJobType.JELLYFIN_MOVIE_WATCH_HISTORY: SchedulePreset.DAILY,
    SyncJobType.SONARR_IMPORT: SchedulePreset.DAILY,
    SyncJobType.JELLYFIN_SERIES_IMPORT: SchedulePreset.DAILY,
    SyncJobType.JELLYFIN_SERIES_WATCH_HISTORY: SchedulePreset.DAILY,
}
