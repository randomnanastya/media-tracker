import ky, { HTTPError, type KyInstance } from "ky";
import type { AuthErrorResponse } from "../types/auth";

const PUBLIC_PATHS = [
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/status",
  "/api/v1/auth/refresh",
  "/api/v1/auth/reset-password",
];

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

export const apiClient: KyInstance = ky.create({
  prefixUrl: "/",
  credentials: "include",
  hooks: {
    afterResponse: [
      async (request, _options, response) => {
        if (response.status !== 401) return response;

        const url = new URL(request.url);
        if (PUBLIC_PATHS.some((p) => url.pathname === p)) return response;

        if (isRefreshing && refreshPromise) {
          const ok = await refreshPromise;
          if (ok) return ky(request.clone(), { credentials: "include" });
          return response;
        }

        isRefreshing = true;
        refreshPromise = (async () => {
          try {
            await ky.post("/api/v1/auth/refresh", { credentials: "include" });
            return true;
          } catch {
            window.location.href = "/auth";
            return false;
          } finally {
            isRefreshing = false;
            refreshPromise = null;
          }
        })();

        const ok = await refreshPromise;
        if (ok) return ky(request.clone(), { credentials: "include" });
        return response;
      },
    ],
  },
});

export async function parseAuthError(
  error: unknown
): Promise<AuthErrorResponse | null> {
  if (error instanceof HTTPError) {
    try {
      return await error.response.json<AuthErrorResponse>();
    } catch {
      return null;
    }
  }
  return null;
}

export const AUTH_ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: "Invalid username or password",
  AUTH_REGISTRATION_CLOSED: "Registration is not available",
  AUTH_USERNAME_TAKEN: "Username is already taken",
  AUTH_INVALID_RECOVERY_CODE: "Invalid recovery code",
  AUTH_TOKEN_EXPIRED: "Session expired, please sign in again",
  AUTH_TOKEN_INVALID: "Invalid session, please sign in again",
};
