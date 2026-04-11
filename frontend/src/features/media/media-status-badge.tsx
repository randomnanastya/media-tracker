import type { WatchStatus } from "../../types/media";

interface Props {
  status: WatchStatus | null;
}

const CONFIG: Record<WatchStatus, { label: string; className: string }> = {
  watched:  { label: "Watched",  className: "bg-green-500 text-white" },
  watching: { label: "Watching", className: "bg-blue-500 text-white" },
  planned:  { label: "Planned",  className: "bg-amber-500 text-white" },
  dropped:  { label: "Dropped",  className: "bg-gray-600 text-white" },
};

export function MediaStatusBadge({ status }: Props) {
  if (!status) return null;
  const { label, className } = CONFIG[status];
  return (
    <span className={`self-start text-xs px-2 py-0.5 rounded-md font-medium ${className}`}>
      {label}
    </span>
  );
}
