import { apiClient } from "./client";
import type { MediaDetailResponse, MediaListResponse } from "../types/media";

interface MediaListParams {
  type?: string;
  status?: string;
  jellyfin_user_id?: number;
}

export const mediaApi = {
  list: (params?: MediaListParams): Promise<MediaListResponse> =>
    apiClient
      .get("api/v1/media", { searchParams: (params as Record<string, string | number>) ?? {} })
      .json<MediaListResponse>(),
  detail: (id: number): Promise<MediaDetailResponse> =>
    apiClient.get(`api/v1/media/${id}`).json<MediaDetailResponse>(),
};
