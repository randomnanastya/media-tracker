"""Pydantic schemas for sync schedule endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import SchedulePreset, SyncJobType


class SyncScheduleRequest(BaseModel):
    preset: SchedulePreset
    cron_expression: str | None = Field(default=None, max_length=100)


class SyncScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_type: SyncJobType
    preset: SchedulePreset
    cron_expression: str
    is_enabled: bool
    is_running: bool
    last_run_at: datetime | None
    next_run_at: datetime | None


class SyncScheduleListResponse(BaseModel):
    schedules: list[SyncScheduleResponse]


class SyncTriggerResponse(BaseModel):
    job_type: SyncJobType
    message: str
