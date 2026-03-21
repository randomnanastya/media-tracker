export type ServiceType = "radarr" | "sonarr" | "jellyfin";

export interface ServiceConfigResponse {
  service_type: ServiceType;
  url: string;
  masked_api_key: string;
  is_configured: boolean;
}

export interface ServiceConfigListResponse {
  services: ServiceConfigResponse[];
}

export interface ServiceConfigRequest {
  url?: string;
  api_key?: string;
}

export interface ServiceTestRequest {
  url: string;
  api_key?: string;
}

export interface ServiceTestResponse {
  service_type: ServiceType;
  success: boolean;
  message: string;
}
