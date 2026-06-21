import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { MediaDetailResponse, EpisodeDetail } from "../../types/media";
import { mediaApi } from "../../api/media";
import { useJellyfinUser } from "../../contexts/jellyfin-user-context";
import { EpisodeStatusToggle } from "./episode-status-toggle";
import { ResetToJellyfinButton } from "./reset-to-jellyfin-button";

interface EpisodeRowProps {
  episode: EpisodeDetail;
  mediaId: number;
}

function formatDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function formatRuntime(minutes: number | null): string {
  if (!minutes) return "";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return `${h}h ${m}m`;
  if (h > 0) return `${h}h`;
  return `${m}m`;
}

export function MediaEpisodeRow({ episode, mediaId }: EpisodeRowProps) {
  const { selectedUser } = useJellyfinUser();
  const queryClient = useQueryClient();

  const toggleMutation = useMutation({
    mutationFn: () => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      const nextStatus = episode.watch_status === "watched" ? "planned" : "watched";
      return mediaApi.setEpisodeWatchStatus(episode.id, nextStatus, jfId);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const snapshot = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        const nextStatus = episode.watch_status === "watched" ? "planned" : "watched";
        return {
          ...old,
          seasons: old.seasons.map((season) => ({
            ...season,
            episodes: season.episodes.map((ep) =>
              ep.id === episode.id
                ? { ...ep, watch_status: nextStatus, is_manual: true }
                : ep,
            ),
          })),
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

  const resetMutation = useMutation({
    mutationFn: () => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      return mediaApi.clearEpisodeManual(episode.id, jfId);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const snapshot = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        return {
          ...old,
          seasons: old.seasons.map((season) => ({
            ...season,
            episodes: season.episodes.map((ep) =>
              ep.id === episode.id ? { ...ep, is_manual: false } : ep,
            ),
          })),
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

  return (
    <div className="group flex items-center gap-3 px-2 -mx-2 py-2 rounded-md border-b border-[#2a2520]/8 last:border-0 transition-colors duration-100 hover:bg-[#2a2520]/[0.04]">
      <EpisodeStatusToggle
        watched={episode.watch_status === "watched"}
        isManual={episode.is_manual}
        isLoading={toggleMutation.isPending}
        disabled={!selectedUser}
        onClick={() => toggleMutation.mutate()}
      />
      <ResetToJellyfinButton
        isManual={episode.is_manual}
        isLoading={resetMutation.isPending}
        onClick={() => resetMutation.mutate()}
      />
      <span className="text-sm text-[#2a2520]/50 w-5 text-center shrink-0">
        {episode.episode_number}
      </span>
      {episode.thumbnail_url ? (
        <img
          src={episode.thumbnail_url}
          className="w-16 h-9 rounded object-cover shrink-0"
          alt=""
        />
      ) : (
        <div className="w-16 h-9 rounded bg-[#2a2520]/10 shrink-0" />
      )}
      <span className="text-sm flex-1 min-w-0 truncate">{episode.title}</span>
      {episode.air_date && (
        <span className="text-xs text-[#2a2520]/65 shrink-0">
          {formatDate(episode.air_date)}
        </span>
      )}
      <span className="text-xs text-[#2a2520]/65 shrink-0">
        {formatRuntime(episode.runtime_minutes)}
      </span>
    </div>
  );
}
