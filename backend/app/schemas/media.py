from typing import Literal

from pydantic import BaseModel


class MediaItem(BaseModel):
    id: int
    title: str
    media_type: Literal["movie", "series"]
    year: int | None = None
    genres: list[str] = []
    poster_url: str | None = None
    rating: float | None = None
    watch_status: Literal["watched", "watching", "planned", "dropped"] | None = None
    total_episodes: int | None = None
    watched_episodes: int | None = None


class MediaListResponse(BaseModel):
    items: list[MediaItem]
    total: int


class MediaDetailResponse(BaseModel):
    id: int
    media_type: Literal["movie", "series"]
    title: str
    year: int | None = None
    poster_url: str | None = None
    backdrop_path: str | None = None
    overview: str | None = None
    genres: list[str] = []
    status: str | None = None
    tmdb_rating_percent: int | None = None
    watch_status: Literal["watched", "watching", "planned", "dropped"] | None = None
    tmdb_id: str | None = None
    imdb_id: str | None = None
    tvdb_id: str | None = None
