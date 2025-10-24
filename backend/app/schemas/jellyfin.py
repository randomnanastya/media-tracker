from pydantic import BaseModel

from app.schemas.responses import ErrorDetail


class JellyfinUsersResponse(BaseModel):
    status: str = "success"
    imported_count: int = 0
    updated_count: int = 0
    error: ErrorDetail | None = None


class JellyfinMoviesSyncResponse(BaseModel):
    status: str
    synced_count: int
    updated_count: int
    added_count: int
