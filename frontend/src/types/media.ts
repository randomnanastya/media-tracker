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
