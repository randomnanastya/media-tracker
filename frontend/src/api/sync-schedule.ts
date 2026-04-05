import { apiClient } from "./client";
import type {
  SyncScheduleListResponse,
  SyncScheduleRequest,
  SyncScheduleResponse,
  SyncJobType,
  SyncTriggerResponse,
} from "../types/sync-schedule";

export const syncScheduleApi = {
  list: () =>
    apiClient.get("api/v1/settings/schedules").json<SyncScheduleListResponse>(),

  update: (jobType: SyncJobType, data: SyncScheduleRequest) =>
    apiClient
      .put(`api/v1/settings/schedules/${jobType}`, { json: data })
      .json<SyncScheduleResponse>(),

  trigger: (jobType: SyncJobType) =>
    apiClient
      .post(`api/v1/sync/trigger/${jobType}`)
      .json<SyncTriggerResponse>(),
};
