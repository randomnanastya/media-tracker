import { apiClient } from "./client";
import type { JellyfinUser } from "../types/user";

export const usersApi = {
  listJellyfinUsers: (): Promise<JellyfinUser[]> =>
    apiClient.get("api/v1/users").json<JellyfinUser[]>(),
};
