import { useState } from "react";
import type { SeasonDetail } from "../../types/media";
import { MediaSeasonRow } from "./media-season-row";

interface Props {
  seasons: SeasonDetail[];
}

export function MediaSeasonsSection({ seasons }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggle = (n: number) => setExpanded(prev => {
    const next = new Set(prev);
    next.has(n) ? next.delete(n) : next.add(n);
    return next;
  });

  const sorted = [...seasons].sort((a, b) => {
    if (a.number === 0) return 1;
    if (b.number === 0) return -1;
    return a.number - b.number;
  });

  const episodesTotal = seasons.reduce((sum, s) => sum + s.total_episodes, 0);
  const watchedTotal = seasons.reduce((sum, s) => sum + s.watched_episodes, 0);

  return (
    <section className="flex flex-col gap-3">
      <header className="flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-[#2a2520]/75 uppercase tracking-wide">
          Seasons
        </h2>
        <p className="text-sm font-medium text-[#2a2520]/65 tabular-nums">
          {seasons.length} seasons · {watchedTotal} / {episodesTotal} episodes
        </p>
      </header>
      <div className="flex flex-col gap-3 sm:gap-4">
        {sorted.map(s => (
          <MediaSeasonRow
            key={s.number}
            season={s}
            isExpanded={expanded.has(s.number)}
            onToggle={() => toggle(s.number)}
          />
        ))}
      </div>
    </section>
  );
}
