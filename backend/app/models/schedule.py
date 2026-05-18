import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServiceType(enum.Enum):
    RADARR = "radarr"
    SONARR = "sonarr"
    JELLYFIN = "jellyfin"


class SchedulePreset(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class SyncJobType(enum.Enum):
    JELLYFIN_USERS_IMPORT = "jellyfin_users_import"
    RADARR_IMPORT = "radarr_import"
    JELLYFIN_MOVIES_IMPORT = "jellyfin_import_movies"
    JELLYFIN_MOVIE_WATCH_HISTORY = "jellyfin_movie_watch_history"
    SONARR_IMPORT = "sonarr_import"
    JELLYFIN_SERIES_IMPORT = "jellyfin_import_series"
    JELLYFIN_SERIES_WATCH_HISTORY = "jellyfin_series_watch_history"
    TMDB_METADATA_UPDATE = "tmdb_metadata_update"


class SyncSchedule(Base):
    __tablename__ = "sync_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[SyncJobType] = mapped_column(Enum(SyncJobType), nullable=False, unique=True)
    preset: Mapped[SchedulePreset] = mapped_column(Enum(SchedulePreset), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    is_running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ServiceConfig(Base):
    __tablename__ = "service_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_type: Mapped[ServiceType] = mapped_column(
        Enum(ServiceType), nullable=False, unique=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
