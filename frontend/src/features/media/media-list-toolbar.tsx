import type { ViewMode, WatchStatus } from "../../types/media";
import { MediaStatusFilter } from "./media-status-filter";
import { MediaViewToggle } from "./media-view-toggle";

interface Props {
  status: WatchStatus | null;
  onStatusChange: (status: WatchStatus | null) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export function MediaListToolbar({ status, onStatusChange, viewMode, onViewModeChange }: Props) {
  return (
    <div className="flex items-center gap-3">
      <MediaStatusFilter value={status} onChange={onStatusChange} />
      <MediaViewToggle value={viewMode} onChange={onViewModeChange} />
    </div>
  );
}
