export type MediaType = "movie" | "series";
export type WatchStatus = "watched" | "watching" | "planned" | "dropped";
export type ViewMode = "list" | "grid";

export interface MediaItem {
  id: number;
  title: string;
  media_type: MediaType;
  year: number | null;
  genres: string[];
  poster_url: string | null;
  rating: number | null;
  watch_status: WatchStatus | null;
  total_episodes: number | null;
  watched_episodes: number | null;
}

export interface MediaListResponse {
  items: MediaItem[];
  total: number;
}

export interface EpisodeDetail {
  number: number;
  title: string;
  air_date: string | null;
  still_url: string | null;
  watch_status: WatchStatus | null;
}

export interface SeasonDetail {
  number: number;
  poster_url: string | null;
  vote_average: number | null;
  release_date: string | null;
  total_episodes: number;
  watched_episodes: number;
  episodes: EpisodeDetail[];
}

export interface MediaDetailResponse {
  id: number;
  media_type: MediaType;
  title: string;
  year: number | null;
  poster_url: string | null;
  backdrop_path: string | null;
  overview: string | null;
  genres: string[];
  status: string | null;
  tmdb_rating_percent: number | null;
  watch_status: WatchStatus | null;
  tmdb_id: string | null;
  imdb_id: string | null;
  tvdb_id: string | null;
  seasons: SeasonDetail[];
}
