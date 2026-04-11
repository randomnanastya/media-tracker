import { Star } from "lucide-react";
import type { MediaItem } from "../../types/media";
import { MediaPoster } from "./media-poster";
import { MediaStatusBadge } from "./media-status-badge";
import { MediaProgressBar } from "./media-progress-bar";

interface Props {
  item: MediaItem;
}

export function MediaGridCard({ item }: Props) {
  return (
    <div className="flex flex-col bg-white/80 border border-[#c9b89a]/30 rounded-xl overflow-hidden">
      <div className="relative">
        <MediaPoster
          src={item.poster_url}
          alt={item.title}
          className="w-full aspect-[2/3] rounded-t-xl"
        />
        {item.watch_status && (
          <div className="absolute top-2 right-2">
            <MediaStatusBadge status={item.watch_status} />
          </div>
        )}
      </div>
      <div className="p-2 flex flex-col gap-1">
        <div className="flex items-center justify-between gap-1">
          <span className="text-sm font-medium text-[#2a2520] truncate">{item.title}</span>
          {item.rating !== null && (
            <div className="flex items-center gap-0.5 shrink-0">
              <Star size={10} className="text-[#ffb826] fill-[#ffb826]" />
              <span className="text-xs text-[#8B6914]">{item.rating.toFixed(1)}</span>
            </div>
          )}
        </div>
        {item.year && <p className="text-xs text-[#2a2520]/65">{item.year}</p>}
        {item.genres.length > 0 && (
          <p className="text-xs text-[#2a2520]/65 truncate">{item.genres.join(", ")}</p>
        )}
        {item.media_type === "series" &&
          item.total_episodes !== null &&
          item.watched_episodes !== null && (
            <MediaProgressBar watched={item.watched_episodes} total={item.total_episodes} />
          )}
      </div>
    </div>
  );
}
