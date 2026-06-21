import { useState, useRef, useEffect } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mediaApi } from "../../api/media";
import { useJellyfinUser } from "../../contexts/jellyfin-user-context";
import type { MediaDetailResponse, WatchStatus } from "../../types/media";

function formatWatchedDate(value: string | null): string {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

const STATUS_OPTIONS: WatchStatus[] = ["planned", "watching", "watched", "dropped"];

const STATUS_CONFIG: Record<WatchStatus, { label: string; dotClass: string }> = {
  planned:  { label: "Planned",  dotClass: "bg-amber-500" },
  watching: { label: "Watching", dotClass: "bg-blue-500" },
  watched:  { label: "Watched",  dotClass: "bg-green-500" },
  dropped:  { label: "Dropped",  dotClass: "bg-gray-500" },
};

interface MovieWatchToggleProps {
  mediaId: number;
  status: WatchStatus | null;
  isManual: boolean;
  watchedAt: string | null;
}

export function MovieWatchToggle({ mediaId, status, isManual, watchedAt }: MovieWatchToggleProps) {
  const { selectedUser } = useJellyfinUser();
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const { mutate, isPending } = useMutation({
    mutationFn: (newStatus: WatchStatus) => {
      const jfId = selectedUser?.jellyfin_user_id;
      if (!jfId) return Promise.reject(new Error("No Jellyfin user"));
      return mediaApi.setMovieWatchStatus(mediaId, newStatus, jfId);
    },
    onMutate: async (newStatus) => {
      setIsOpen(false);
      await queryClient.cancelQueries({ queryKey: ["media", mediaId] });
      const previous = queryClient.getQueryData<MediaDetailResponse>(["media", mediaId]);
      queryClient.setQueryData<MediaDetailResponse>(["media", mediaId], (old) => {
        if (!old) return old;
        return { ...old, watch_status: newStatus, is_manual: true };
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

  const manualRing = isManual ? "ring-2 ring-[#96551d] ring-offset-1" : "";

  if (!selectedUser) {
    return (
      <button
        type="button"
        disabled
        title="Select a Jellyfin user first"
        className="w-full sm:w-auto px-4 py-2 rounded-lg font-medium flex items-center gap-2 bg-[#2a2520]/10 text-[#2a2520]/40 cursor-not-allowed"
      >
        <span className="w-2.5 h-2.5 rounded-full bg-[#2a2520]/20 shrink-0" />
        Set status
        <ChevronDown size={14} className="opacity-50 ml-auto" />
      </button>
    );
  }

  const currentConfig = status ? STATUS_CONFIG[status] : null;
  const dateLabel = status === "watched" ? formatWatchedDate(watchedAt) : null;

  return (
    <div ref={containerRef} className="relative w-full sm:w-auto">
      <button
        type="button"
        disabled={isPending}
        onClick={() => setIsOpen((v) => !v)}
        className={`w-full sm:w-auto justify-between px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors bg-[#ffb826] text-[#2a2520] hover:bg-[#f5a93a] ${manualRing}`}
      >
        {isPending ? (
          <Loader2 size={16} className="animate-spin shrink-0" />
        ) : (
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${currentConfig ? currentConfig.dotClass : "bg-[#2a2520]/20"}`}
          />
        )}
        <span>
          {currentConfig ? currentConfig.label : "Set status"}
          {dateLabel && <span className="font-normal opacity-70"> · {dateLabel}</span>}
        </span>
        <ChevronDown size={14} className={`transition-transform ml-1 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-1 z-20 bg-white shadow-lg rounded-xl border border-[#c9b89a]/30 py-1 min-w-[160px]">
          {STATUS_OPTIONS.map((s) => {
            const cfg = STATUS_CONFIG[s];
            return (
              <button
                key={s}
                type="button"
                onClick={() => mutate(s)}
                className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 hover:bg-[#f5f0e8] transition-colors ${status === s ? "font-semibold" : ""}`}
              >
                <span className={`w-2 h-2 rounded-full shrink-0 ${cfg.dotClass}`} />
                {cfg.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
