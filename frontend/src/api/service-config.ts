import { apiClient } from "./client";
import type {
  ServiceConfigListResponse,
  ServiceConfigRequest,
  ServiceConfigResponse,
  ServiceTestRequest,
  ServiceTestResponse,
  ServiceType,
} from "../types/service-config";

export const serviceConfigApi = {
  list: () =>
    apiClient.get("api/v1/settings/services").json<ServiceConfigListResponse>(),

  upsert: (service: ServiceType, data: ServiceConfigRequest) =>
    apiClient
      .put(`api/v1/settings/services/${service}`, { json: data })
      .json<ServiceConfigResponse>(),

  test: (service: ServiceType, data: ServiceTestRequest) =>
    apiClient
      .post(`api/v1/settings/services/${service}/test`, { json: data })
      .json<ServiceTestResponse>(),
};
