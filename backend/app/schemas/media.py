from pydantic import BaseModel


class MediaItem(BaseModel):
    id: int
    title: str
    media_type: str  # "movie" | "series"
    year: int | None = None
    genres: list[str] = []
    poster_url: str | None = None
    rating: float | None = None
    watch_status: str | None = None  # "planned" | "watching" | "watched" | "dropped"
    total_episodes: int | None = None
    watched_episodes: int | None = None


class MediaListResponse(BaseModel):
    items: list[MediaItem]
    total: int
