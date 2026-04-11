import { useCallback, useState } from "react";
import { useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Film } from "lucide-react";
import { mediaApi } from "../api/media";
import { MediaListHeader } from "../features/media/media-list-header";
import { MediaListToolbar } from "../features/media/media-list-toolbar";
import { MediaListView } from "../features/media/media-list-view";
import { MediaGridView } from "../features/media/media-grid-view";
import type { MediaType, ViewMode, WatchStatus } from "../types/media";

interface Props {
  type?: MediaType;
}

const VIEW_MODE_KEY = "media-view-mode";

export function MediaListPage({ type }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const status = (searchParams.get("status") as WatchStatus | null) ?? null;

  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    return (localStorage.getItem(VIEW_MODE_KEY) as ViewMode) ?? "list";
  });

  const handleStatusChange = useCallback((newStatus: WatchStatus | null) => {
    setSearchParams(newStatus ? { status: newStatus } : {});
  }, [setSearchParams]);

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem(VIEW_MODE_KEY, mode);
  }, []);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["media", { type, status }],
    queryFn: () => mediaApi.list({ type, status: status ?? undefined }),
  });

  if (isLoading) {
    return <MediaListSkeleton viewMode={viewMode} />;
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-[#2a2520]/70">
        <p>Failed to load media</p>
        <button type="button" onClick={() => refetch()} className="text-sm underline">
          Retry
        </button>
      </div>
    );
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const isEmpty = items.length === 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <MediaListHeader type={type} total={total} />
        <MediaListToolbar
          status={status}
          onStatusChange={handleStatusChange}
          viewMode={viewMode}
          onViewModeChange={handleViewModeChange}
        />
      </div>

      {isEmpty ? (
        <EmptyState />
      ) : viewMode === "list" ? (
        <MediaListView items={items} />
      ) : (
        <MediaGridView items={items} />
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 py-24 text-[#2a2520]/70">
      <Film size={48} className="text-[#2a2520]/20" aria-hidden="true" />
      <p className="font-medium text-[#2a2520]">No media found</p>
      <p className="text-sm text-center max-w-sm">
        Your media library is empty. Import data from Radarr or Sonarr in{" "}
        <a href="/settings" className="underline">Settings</a>.
      </p>
    </div>
  );
}

function MediaListSkeleton({ viewMode }: { viewMode: ViewMode }) {
  if (viewMode === "grid") {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2 animate-pulse">
            <div className="w-full aspect-[2/3] bg-[#2a2520]/10 rounded-xl" />
            <div className="h-3 bg-[#2a2520]/10 rounded w-3/4" />
            <div className="h-3 bg-[#2a2520]/10 rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex gap-3 p-3 bg-white/40 border border-[#c9b89a]/30 rounded-xl animate-pulse">
          <div className="w-20 h-[110px] bg-[#2a2520]/10 rounded-lg shrink-0" />
          <div className="flex flex-col gap-2 flex-1">
            <div className="h-4 bg-[#2a2520]/10 rounded w-2/3" />
            <div className="h-3 bg-[#2a2520]/10 rounded w-1/2" />
            <div className="h-3 bg-[#2a2520]/10 rounded w-1/4" />
          </div>
        </div>
      ))}
    </div>
  );
}
