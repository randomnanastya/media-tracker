import { SeasonDetail } from "../../types/media";
import { MediaEpisodeRow } from "./media-episode-row";
import { SeasonBulkActions } from "./season-bulk-actions";
import { CheckCircle2, ChevronDown } from "lucide-react";

interface SeasonRowProps {
  season: SeasonDetail;
  mediaId: number;
  isExpanded: boolean;
  onToggle: () => void;
}

export function MediaSeasonRow({ season, mediaId, isExpanded, onToggle }: SeasonRowProps) {
  const year = season.release_date ? new Date(season.release_date).getFullYear() : null;
  const pct =
    season.total_episodes > 0
      ? Math.round((season.watched_episodes / season.total_episodes) * 100)
      : 0;
  const completed = season.total_episodes > 0 && season.watched_episodes >= season.total_episodes;

  return (
    <div className="rounded-xl overflow-hidden bg-white border border-[#c9b89a]/30">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={`season-${season.number}-episodes`}
        className={`w-full flex items-center gap-3 text-left p-3 sm:p-4 transition-colors duration-150 hover:bg-[#ffb826]/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/60 focus-visible:ring-inset active:bg-[#ffb826]/[0.14] group ${isExpanded ? "border-b border-[#c9b89a]/40" : ""}`}
      >
        <div className="flex-1 min-w-0">
          <p className="text-base font-semibold text-[#2a2520]">
            {season.number === 0 ? "Specials" : `Season ${season.number}`}
            {year !== null && (
              <span className="text-sm font-normal text-[#2a2520]/65"> · {year}</span>
            )}
            <span className="text-sm font-normal text-[#2a2520]/65"> · {season.total_episodes} episodes</span>
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {season.vote_average !== null && (
            <span className="text-sm font-semibold text-[#2a2520]">
              {Math.round(season.vote_average * 10)}%
            </span>
          )}
          {season.total_episodes > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-[#2a2520]/65 tabular-nums shrink-0 whitespace-nowrap">
                {season.watched_episodes}/{season.total_episodes}
              </span>
              <div
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Season ${season.number === 0 ? "Specials" : season.number} progress`}
                className="w-24 sm:w-32 h-1.5 rounded-full bg-[#2a2520]/10"
              >
                <div
                  className="h-full rounded-full bg-[#ffb826]"
                  style={{ width: `${pct}%` }}
                />
              </div>
              {completed && (
                <CheckCircle2 className="text-green-600" size={18} aria-label="Completed" />
              )}
            </div>
          )}
          <ChevronDown
            size={16}
            className={`transition-colors text-[#2a2520]/50 group-hover:text-[#2a2520]/80 ${isExpanded ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </div>
      </button>

      <div
        id={`season-${season.number}-episodes`}
        hidden={!isExpanded}
        className="px-4 pt-2 pb-3 bg-white"
      >
        <div className="px-4 py-2 border-b border-[#2a2520]/10">
          <SeasonBulkActions seasonId={season.id} mediaId={mediaId} />
        </div>
        {season.episodes.length === 0 ? (
          <p className="py-4 text-sm text-black/50">No episodes</p>
        ) : (
          season.episodes.map((ep) => <MediaEpisodeRow key={ep.episode_number} episode={ep} mediaId={mediaId} />)
        )}
      </div>
    </div>
  );
}
