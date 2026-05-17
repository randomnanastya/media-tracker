import { Check, Star } from "lucide-react";
import type { SeasonDetail } from "../../types/media";
import { MediaPoster } from "./media-poster";
import { MediaProgressBar } from "./media-progress-bar";

interface SeasonCardProps {
  season: SeasonDetail;
}

function MediaSeasonCard({ season }: SeasonCardProps) {
  const label = season.number === 0 ? "Specials" : `Season ${season.number}`;
  const isFullyWatched =
    season.total_episodes > 0 && season.watched_episodes >= season.total_episodes;
  const ratingPercent =
    season.vote_average !== null ? Math.round(season.vote_average * 10) : null;
  const releaseYear = season.release_date
    ? new Date(season.release_date).getFullYear()
    : null;

  return (
    <article
      className="flex flex-col bg-white/80 border border-[#c9b89a]/30 rounded-xl overflow-hidden transition-shadow hover:shadow-md hover:shadow-[rgba(150,85,29,0.08)]"
      aria-label={`${label}, ${season.watched_episodes} of ${season.total_episodes} episodes watched${ratingPercent !== null ? `, rated ${ratingPercent}%` : ""}`}
    >
      <div className="relative">
        <MediaPoster
          src={season.poster_url}
          alt={label}
          className="w-full aspect-[2/3] rounded-t-xl"
        />
        {isFullyWatched && (
          <span className="absolute bottom-2 right-2 flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md bg-green-500 text-white shadow">
            <Check size={12} aria-hidden="true" /> Completed
          </span>
        )}
      </div>
      <div className="p-1.5 flex flex-col gap-0.5">
        <div className="flex items-center justify-between gap-1">
          <span className="text-xs font-semibold text-[#2a2520] truncate">{label}</span>
          {ratingPercent !== null && (
            <div className="flex items-center gap-0.5 shrink-0 tabular-nums">
              <Star size={10} className="text-[#ffb826] fill-[#ffb826]" aria-hidden="true" />
              <span className="text-xs font-bold text-[#2a2520]">{ratingPercent}%</span>
            </div>
          )}
        </div>
        {releaseYear && (
          <p className="text-xs text-[#2a2520]/50 tabular-nums">{releaseYear}</p>
        )}
        <MediaProgressBar watched={season.watched_episodes} total={season.total_episodes} />
      </div>
    </article>
  );
}

interface Props {
  seasons: SeasonDetail[];
}

export function MediaSeasonsSection({ seasons }: Props) {
  const sortedSeasons = [...seasons].sort((a, b) => {
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
        <p className="text-sm text-[#2a2520]/65 tabular-nums">
          {seasons.length} seasons · {watchedTotal} / {episodesTotal} episodes
        </p>
      </header>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-3">
        {sortedSeasons.map((s) => (
          <MediaSeasonCard key={s.number} season={s} />
        ))}
      </div>
    </section>
  );
}
