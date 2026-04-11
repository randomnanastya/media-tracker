import type { WatchStatus } from "../../types/media";

interface Props {
  status: WatchStatus | null;
}

const CONFIG: Record<WatchStatus, { label: string; className: string }> = {
  watched:  { label: "Watched",  className: "bg-green-500/15 text-green-700" },
  watching: { label: "Watching", className: "bg-[#ffb826]/15 text-[#7a5c10]" },
  planned:  { label: "Planned",  className: "bg-gray-200 text-gray-600" },
  dropped:  { label: "Dropped",  className: "bg-red-500/15 text-red-700" },
};

export function MediaStatusBadge({ status }: Props) {
  if (!status) return null;
  const { label, className } = CONFIG[status];
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${className}`}>
      {label}
    </span>
  );
}
