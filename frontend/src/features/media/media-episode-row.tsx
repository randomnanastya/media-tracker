import { EpisodeDetail } from "../../types/media";
import { MediaEpisodeThumb } from "./media-episode-thumb";
import { WATCH_STATUS_DOT_COLOR } from "./watch-status-colors";

interface EpisodeRowProps { episode: EpisodeDetail }

export function MediaEpisodeRow({ episode }: EpisodeRowProps) {
  const formattedDate = episode.air_date
    ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(
        new Date(episode.air_date),
      )
    : null;

  return (
    <div className="flex items-center gap-3 px-2 -mx-2 py-2 rounded-md border-b border-[#2a2520]/8 last:border-0 transition-colors duration-100 hover:bg-[#2a2520]/[0.04]">
      <span className="w-7 shrink-0 text-right text-sm font-medium text-[#2a2520]/55 tabular-nums">{episode.number}</span>
      <MediaEpisodeThumb
        src={episode.still_url}
        alt={episode.title}
        className="w-28 sm:w-36 shrink-0 rounded-lg"
      />
      <span className="flex-1 text-sm font-semibold text-[#2a2520] truncate min-w-0" title={episode.title}>{episode.title}</span>
      <span className="w-24 shrink-0 text-xs text-[#2a2520]/55 tabular-nums text-right">{formattedDate ?? ""}</span>
      <div className="shrink-0">
        {episode.watch_status !== null ? (
          <button
            type="button"
            aria-label="episode status"
            className="p-2 -m-2 rounded-full transition-transform duration-100 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/60"
          >
            <span
              className={`block w-3 h-3 rounded-full ${WATCH_STATUS_DOT_COLOR[episode.watch_status]}`}
              aria-label={episode.watch_status}
            />
          </button>
        ) : (
          <button
            type="button"
            aria-label="episode status"
            className="p-2 -m-2 rounded-full transition-transform duration-100 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/60"
          >
            <span
              className="block w-3 h-3 rounded-full border border-[#2a2520]/45"
              aria-label="not watched"
            />
          </button>
        )}
      </div>
    </div>
  );
}
