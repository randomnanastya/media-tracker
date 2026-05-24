from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class ManualWatchStatus(StrEnum):
    WATCHED = "watched"
    PLANNED = "planned"


class WatchStatusUpdateRequest(BaseModel):
    jellyfin_user_id: str
    status: ManualWatchStatus


class WatchHistoryItem(BaseModel):
    media_id: int
    episode_id: int | None
    status: Literal["watched", "watching", "planned", "dropped"]
    is_manual: bool
    watched_at: datetime | None


class WatchStatusUpdateResponse(BaseModel):
    item: WatchHistoryItem


class BulkWatchStatusRequest(BaseModel):
    jellyfin_user_id: str
    status: ManualWatchStatus


class BulkWatchStatusResponse(BaseModel):
    affected: int
    inserted: int
    updated: int


class ResetManualRequest(BaseModel):
    jellyfin_user_id: str
