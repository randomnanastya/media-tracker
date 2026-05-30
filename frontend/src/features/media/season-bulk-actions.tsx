import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mediaApi } from "../../api/media";
import { useJellyfinUser } from "../../contexts/jellyfin-user-context";
import type { MediaDetailResponse } from "../../types/media";

interface SeasonBulkActionsProps {
  seasonId: number;
  mediaId: number;
}

export function SeasonBulkActions({ seasonId, mediaId }: SeasonBulkActionsProps) {
  const { selectedUser } = useJellyfinUser();
  const queryClient = useQueryClient();

  const markWatched = useMutation({
    mutationFn: () => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      return mediaApi.setSeasonWatchStatus(seasonId, "watched", jfId);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const snapshot = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        return {
          ...old,
          seasons: old.seasons.map((s) =>
            s.id === seasonId
              ? {
                  ...s,
                  episodes: s.episodes.map((ep) => ({
                    ...ep,
                    watch_status: "watched" as const,
                    is_manual: true,
                  })),
                }
              : s,
          ),
        };
      });
      return { snapshot };
    },
    onError: (_err, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(["media", mediaId], context.snapshot);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["media", mediaId] });
    },
  });

  const markUnwatched = useMutation({
    mutationFn: () => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      return mediaApi.setSeasonWatchStatus(seasonId, "planned", jfId);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const snapshot = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        return {
          ...old,
          seasons: old.seasons.map((s) =>
            s.id === seasonId
              ? {
                  ...s,
                  episodes: s.episodes.map((ep) => ({
                    ...ep,
                    watch_status: "planned" as const,
                    is_manual: true,
                  })),
                }
              : s,
          ),
        };
      });
      return { snapshot };
    },
    onError: (_err, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(["media", mediaId], context.snapshot);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["media", mediaId] });
    },
  });

  const isLoading = markWatched.isPending || markUnwatched.isPending;
  const loadingClass = isLoading ? "opacity-50 pointer-events-none" : "";
  const noUserClass = !selectedUser ? "opacity-40 cursor-not-allowed" : "";
  const noUserTitle = !selectedUser ? "Select a Jellyfin user first" : undefined;
  const [statusMsg, setStatusMsg] = useState("");

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-[#2a2520]/65">
      <span role="status" aria-live="polite" className="sr-only">{statusMsg}</span>
      <button
        type="button"
        className={`py-1 px-1 -m-1 hover:text-[#2a2520] transition-colors ${loadingClass} ${noUserClass}`}
        title={noUserTitle}
        disabled={!selectedUser || isLoading}
        onClick={() => markWatched.mutate(undefined, { onSuccess: () => setStatusMsg("All episodes marked as watched") })}
      >
        ✓ Mark all as watched
      </button>
      <span aria-hidden="true">·</span>
      <button
        type="button"
        className={`py-1 px-1 -m-1 hover:text-[#2a2520] transition-colors ${loadingClass} ${noUserClass}`}
        title={noUserTitle}
        disabled={!selectedUser || isLoading}
        onClick={() => markUnwatched.mutate(undefined, { onSuccess: () => setStatusMsg("All episodes marked as unwatched") })}
      >
        Mark all as unwatched
      </button>
    </div>
  );
}
