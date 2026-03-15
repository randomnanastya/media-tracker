import { apiClient } from "./client";
import type {
  AuthStatusResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
  UserResponse,
} from "../types/auth";

export const authApi = {
  getStatus: () =>
    apiClient.get("api/v1/auth/status").json<AuthStatusResponse>(),

  login: (data: LoginRequest) =>
    apiClient.post("api/v1/auth/login", { json: data }).json<LoginResponse>(),

  register: (data: RegisterRequest) =>
    apiClient
      .post("api/v1/auth/register", { json: data })
      .json<RegisterResponse>(),

  resetPassword: (data: ResetPasswordRequest) =>
    apiClient
      .post("api/v1/auth/reset-password", { json: data })
      .json<ResetPasswordResponse>(),

  getMe: () => apiClient.get("api/v1/auth/me").json<UserResponse>(),

  logout: () =>
    apiClient.post("api/v1/auth/logout").json<{ message: string }>(),
};
