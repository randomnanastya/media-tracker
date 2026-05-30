import { Eye, CheckCircle2, Loader2 } from "lucide-react";

function formatWatchedDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mediaApi } from "../../api/media";
import { useJellyfinUser } from "../../contexts/jellyfin-user-context";
import type { MediaDetailResponse } from "../../types/media";

interface MovieWatchToggleProps {
  mediaId: number;
  watched: boolean;
  isManual: boolean;
  watchedAt: string | null;
  disabled?: boolean;
}

export function MovieWatchToggle({
  mediaId,
  watched,
  isManual,
  watchedAt,
  disabled = false,
}: MovieWatchToggleProps) {
  const { selectedUser } = useJellyfinUser();
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: () => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      return mediaApi.setMovieWatchStatus(mediaId, watched ? "planned" : "watched", jfId);
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const previous = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        return {
          ...old,
          watch_status: watched ? "planned" : "watched",
          is_manual: true,
        };
      });
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["media", mediaId], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["media", mediaId] });
    },
  });

  const isDisabled = disabled || !selectedUser || isPending;

  const manualRing = isManual ? "ring-2 ring-[#96551d] ring-offset-1" : "";
  const baseClass = `w-full sm:w-auto justify-center px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${manualRing}`;

  if (!selectedUser) {
    return (
      <button
        type="button"
        disabled
        title="Select a Jellyfin user first"
        className={`${baseClass} bg-[#2a2520]/10 text-[#2a2520]/40 cursor-not-allowed`}
      >
        <Eye size={16} />
        Mark as watched
      </button>
    );
  }

  if (watched) {
    const dateLabel = formatWatchedDate(watchedAt);
    return (
      <button
        type="button"
        disabled={isDisabled}
        onClick={() => mutate()}
        className={`${baseClass} bg-[#ffb826] text-[#2a2520] hover:bg-[#f5a93a]`}
      >
        {isPending ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <CheckCircle2 size={16} />
        )}
        <span>
          Watched{dateLabel ? <span className="font-normal opacity-70"> · {dateLabel}</span> : null}
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={isDisabled}
      onClick={() => mutate()}
      className={`${baseClass} bg-[#ffb826] text-[#2a2520] hover:bg-[#f5a93a]`}
    >
      {isPending ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <Eye size={16} />
      )}
      Mark as watched
    </button>
  );
}
