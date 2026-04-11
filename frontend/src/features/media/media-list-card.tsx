import { Star } from "lucide-react";
import type { MediaItem } from "../../types/media";
import { MediaPoster } from "./media-poster";
import { MediaStatusBadge } from "./media-status-badge";
import { MediaProgressBar } from "./media-progress-bar";

interface Props {
  item: MediaItem;
}

export function MediaListCard({ item }: Props) {
  const metaParts = [
    item.year?.toString(),
    item.genres.join(", ") || undefined,
    item.media_type === "movie" ? "Movie" : "Series",
  ].filter(Boolean);

  return (
    <div className="flex gap-3 p-3 bg-white/40 border border-[#c9b89a]/30 rounded-xl">
      <MediaPoster
        src={item.poster_url}
        alt={item.title}
        className="w-20 h-[110px] rounded-lg shrink-0"
      />
      <div className="flex flex-col gap-1 flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <span className="font-semibold text-[#2a2520] truncate">{item.title}</span>
          {item.rating !== null && (
            <div className="flex items-center gap-1 shrink-0">
              <Star size={12} className="text-[#ffb826] fill-[#ffb826]" />
              <span className="text-xs text-[#8B6914]">{item.rating.toFixed(1)}</span>
            </div>
          )}
        </div>
        <p className="text-sm text-[#2a2520]/70">{metaParts.join(" · ")}</p>
        <MediaStatusBadge status={item.watch_status} />
        {item.media_type === "series" &&
          item.total_episodes !== null &&
          item.watched_episodes !== null && (
            <MediaProgressBar watched={item.watched_episodes} total={item.total_episodes} />
          )}
      </div>
    </div>
  );
}
