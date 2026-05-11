from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.responses import ErrorDetail


class TmdbGenre(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str


class TmdbBridgeMovieResponse(BaseModel):
    """Ответ Bridge API GET /tmdb/movie/{tmdb_id}.

    Поля runtime/budget/revenue/popularity/production_countries/spoken_languages/
    homepage намеренно не объявлены — мы их не сохраняем; extra='ignore' не падает.
    """

    model_config = ConfigDict(extra="ignore")

    tmdb_id: int
    title: str | None = None
    original_title: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    status: str | None = None
    release_date: date | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    genres: list[TmdbGenre] = []
    fetched_at: datetime | None = None
    poster_url: str | None = None


class TmdbMetadataUpdateResponse(BaseModel):
    status: str = "success"
    processed_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    error: ErrorDetail | None = None


class TmdbBridgeEpisodeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tmdb_episode_id: int | None = None
    episode_number: int
    season_number: int
    name: str | None = None
    overview: str | None = None
    still_url: str | None = None
    air_date: date | None = None
    episode_type: str | None = None
    vote_average: float | None = None


class TmdbBridgeSeasonResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tmdb_id: int | None = None
    season_number: int
    overview: str | None = None
    poster_path: str | None = None
    air_date: date | None = None
    vote_average: float | None = None
    poster_url: str | None = None
    episodes: list[TmdbBridgeEpisodeResponse] = []


class TmdbBridgeSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tmdb_id: int
    name: str | None = None
    original_name: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    status: str | None = None
    first_air_date: date | None = None
    last_air_date: date | None = None
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    vote_average: float | None = None
    genres: list[TmdbGenre] = []
    seasons: list[TmdbBridgeSeasonResponse] = []
    fetched_at: datetime | None = None
    poster_url: str | None = None
