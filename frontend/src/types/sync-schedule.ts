export type SyncJobType =
  | "jellyfin_users_import"
  | "radarr_import"
  | "jellyfin_import_movies"
  | "jellyfin_movie_watch_history"
  | "sonarr_import"
  | "jellyfin_import_series"
  | "jellyfin_series_watch_history";

export type SchedulePreset = "daily" | "weekly" | "monthly" | "custom";

export interface SyncScheduleResponse {
  job_type: SyncJobType;
  preset: SchedulePreset;
  cron_expression: string;
  is_enabled: boolean;
  is_running: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface SyncScheduleListResponse {
  schedules: SyncScheduleResponse[];
}

export interface SyncScheduleRequest {
  preset: SchedulePreset;
  cron_expression?: string;
}
