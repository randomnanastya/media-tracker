import type { WatchStatus } from "../../types/media";

export const WATCH_STATUS_DOT_COLOR: Record<WatchStatus, string> = {
  watched:  "bg-green-500",
  watching: "bg-blue-500",
  planned:  "bg-amber-500",
  dropped:  "bg-gray-600",
};
