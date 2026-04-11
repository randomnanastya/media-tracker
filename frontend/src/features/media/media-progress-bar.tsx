interface Props {
  watched: number;
  total: number;
}

export function MediaProgressBar({ watched, total }: Props) {
  if (total === 0) return null;
  const pct = Math.round((watched / total) * 100);

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 h-2 rounded-full bg-[#2a2520]/10"
        role="progressbar"
        aria-valuenow={watched}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label="Episode progress"
      >
        <div
          className="h-full rounded-full bg-[#ffb826]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-[#2a2520]/65 shrink-0">
        {watched} / {total} episodes
      </span>
    </div>
  );
}
