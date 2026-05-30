import { apiClient } from "./client";
import type { MediaDetailResponse, MediaListResponse } from "../types/media";

interface MediaListParams {
  type?: string;
  status?: string;
  jellyfin_user_id?: number;
}

interface WatchStatusUpdateResponse {
  item: {
    media_id: number;
    episode_id: number | null;
    status: string;
    is_manual: boolean;
    watched_at: string | null;
  };
}

interface BulkWatchStatusResponse {
  affected: number;
  inserted: number;
  updated: number;
}

export const mediaApi = {
  list: (params?: MediaListParams): Promise<MediaListResponse> =>
    apiClient
      .get("api/v1/media", { searchParams: (params as Record<string, string | number>) ?? {} })
      .json<MediaListResponse>(),
  detail: (id: number): Promise<MediaDetailResponse> =>
    apiClient.get(`api/v1/media/${id}`).json<MediaDetailResponse>(),
  setMovieWatchStatus: (
    mediaId: number,
    status: "watched" | "planned",
    jellyfinUserId: string,
  ): Promise<WatchStatusUpdateResponse> =>
    apiClient
      .put(`api/v1/watch/movies/${mediaId}`, {
        json: { status, jellyfin_user_id: jellyfinUserId },
      })
      .json(),
  clearMovieManual: (mediaId: number, jellyfinUserId: string): Promise<void> =>
    apiClient
      .delete(`api/v1/watch/movies/${mediaId}/manual`, {
        searchParams: { jellyfin_user_id: jellyfinUserId },
      })
      .then(() => undefined),
  setEpisodeWatchStatus: (
    episodeId: number,
    status: "watched" | "planned",
    jellyfinUserId: string,
  ): Promise<WatchStatusUpdateResponse> =>
    apiClient
      .put(`api/v1/watch/episodes/${episodeId}`, {
        json: { status, jellyfin_user_id: jellyfinUserId },
      })
      .json(),
  clearEpisodeManual: (episodeId: number, jellyfinUserId: string): Promise<void> =>
    apiClient
      .delete(`api/v1/watch/episodes/${episodeId}/manual`, {
        searchParams: { jellyfin_user_id: jellyfinUserId },
      })
      .then(() => undefined),
  setSeasonWatchStatus: (
    seasonId: number,
    status: "watched" | "planned",
    jellyfinUserId: string,
  ): Promise<BulkWatchStatusResponse> =>
    apiClient
      .put(`api/v1/watch/seasons/${seasonId}`, {
        json: { status, jellyfin_user_id: jellyfinUserId },
      })
      .json(),
  setSeriesWatchStatus: (
    mediaId: number,
    status: "watched" | "planned",
    jellyfinUserId: string,
  ): Promise<BulkWatchStatusResponse> =>
    apiClient
      .put(`api/v1/watch/series/${mediaId}`, {
        json: { status, jellyfin_user_id: jellyfinUserId },
      })
      .json(),
  clearSeriesManual: (
    mediaId: number,
    jellyfinUserId: string,
  ): Promise<BulkWatchStatusResponse> =>
    apiClient
      .delete(`api/v1/watch/series/${mediaId}/manual`, {
        json: { jellyfin_user_id: jellyfinUserId },
      })
      .json(),
};
