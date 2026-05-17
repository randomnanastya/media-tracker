import { useEffect } from "react";
import { HTTPError } from "ky";
import { ExternalLink } from "lucide-react";
import tmdbIcon from "../assets/tmdb.svg";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { mediaApi } from "../api/media";
import type { MediaType } from "../types/media";
import { MediaPoster } from "../features/media/media-poster";
import { MediaStatusBadge } from "../features/media/media-status-badge";
import { useDynamicCrumb } from "../contexts/breadcrumb-context";

function getExternalUrl(label: string, value: string, mediaType: MediaType): string | null {
  if (label === "TMDB")
    return `https://www.themoviedb.org/${mediaType === "movie" ? "movie" : "tv"}/${value}`;
  if (label === "IMDB") return `https://www.imdb.com/title/${value}`;
  return null;
}

export function MediaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const numericId = Number(id);
  const isValidId = !!id && !isNaN(numericId);

  const { setDynamicCrumb } = useDynamicCrumb();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["media", numericId],
    queryFn: () => mediaApi.detail(numericId),
    enabled: isValidId,
  });

  useEffect(() => {
    if (data?.title) setDynamicCrumb(data.title);
    return () => setDynamicCrumb(null);
  }, [data?.title, setDynamicCrumb]);

  if (!isValidId) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-2xl font-bold text-[#2a2520]">404</p>
        <p className="text-[#2a2520]/65">Invalid media ID.</p>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm underline text-[#2a2520]/65"
        >
          Go back
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="-mx-6 -mt-6 relative pb-8">
          <div className="h-[380px] sm:h-[480px] bg-[#e4e1d7] animate-pulse" />
          <div className="absolute bottom-0 inset-x-0 px-6 flex gap-4 items-end">
            <div className="w-52 h-80 rounded-xl bg-[#c9b89a]/60 animate-pulse shrink-0" />
            <div className="flex flex-col gap-2 flex-1 pb-2">
              <div className="h-7 w-2/3 rounded bg-[#c9b89a]/60 animate-pulse" />
              <div className="h-4 w-1/3 rounded bg-[#c9b89a]/60 animate-pulse" />
              <div className="h-5 w-1/2 rounded-full bg-[#c9b89a]/60 animate-pulse" />
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-2 max-w-3xl">
          <div className="h-3 w-16 rounded bg-[#e4e1d7] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#e4e1d7] animate-pulse" />
          <div className="h-4 w-5/6 rounded bg-[#e4e1d7] animate-pulse" />
          <div className="h-4 w-4/6 rounded bg-[#e4e1d7] animate-pulse" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    const is404 = error instanceof HTTPError && error.response.status === 404;
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-2xl font-bold text-[#2a2520]">{is404 ? "404" : "Error"}</p>
        <p className="text-[#2a2520]/65">
          {is404 ? "Media not found." : "Failed to load media details."}
        </p>
        {!is404 && (
          <button
            type="button"
            onClick={() => refetch()}
            className="text-sm underline text-[#2a2520]/65"
          >
            Retry
          </button>
        )}
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm underline text-[#2a2520]/65"
        >
          Go back
        </button>
      </div>
    );
  }

  const backdropUrl = data.backdrop_path
    ? `https://image.tmdb.org/t/p/w1280${data.backdrop_path}`
    : null;

  const mediaTypeLabel = data.media_type === "movie" ? "Movie" : "Series";
  const yearAndType = [data.year?.toString(), mediaTypeLabel].filter(Boolean).join(" · ");

  const externalIds = [
    { label: "TMDB", value: data.tmdb_id },
    { label: "IMDB", value: data.imdb_id },
    { label: "TVDB", value: data.tvdb_id },
  ].filter((item): item is { label: string; value: string } => item.value != null);

  return (
    <div className="flex flex-col gap-6">
      {/* Backdrop wrapper: poster is absolutely positioned inside so overview flows normally below */}
      <div className="-mx-6 -mt-6 relative">
        <div className="relative w-full h-[380px] sm:h-[480px] overflow-hidden">
          {backdropUrl ? (
            <>
              <img
                src={backdropUrl}
                alt={data.title}
                className="w-full h-full object-cover object-top"
                fetchPriority="high"
              />
              <div
                className="absolute inset-0"
                style={{ background: "linear-gradient(to bottom, transparent 35%, #f5f1e8 95%)" }}
              />
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "linear-gradient(to right, #f5f1e8 0%, rgba(245,241,232,0.85) 25%, rgba(245,241,232,0.3) 50%, transparent 70%)",
                }}
              />
            </>
          ) : (
            <div className="w-full h-full" style={{ background: "#f5f1e8" }} />
          )}
        </div>

        <div className="absolute top-[80px] sm:top-[130px] inset-x-0 px-6 flex flex-col sm:flex-row gap-4 items-start sm:items-end z-10">
          <div className="relative shrink-0">
            <MediaPoster
              src={data.poster_url}
              alt={data.title}
              className="w-52 h-80 rounded-xl shadow-lg"
            />
            {data.watch_status && (
              <div className="absolute top-2 right-2">
                <MediaStatusBadge status={data.watch_status} />
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2 min-w-0 sm:pb-2">
            <h1 className="text-3xl font-bold text-[#2a2520] leading-tight">{data.title}</h1>

            {(yearAndType || data.status) && (
              <p className="text-base font-medium text-[#2a2520]/80 capitalize">
                {[yearAndType, data.status].filter(Boolean).join(" · ")}
              </p>
            )}

            {data.tmdb_rating_percent !== null && (
              <span className="flex items-center gap-1.5 text-sm font-bold text-[#2a2520]">
                <img src={tmdbIcon} alt="TMDB" className="h-3.5 w-auto" aria-hidden="true" />
                {data.tmdb_rating_percent}%
              </span>
            )}

            {(() => {
              const linkItems = externalIds
                .map(({ label, value }) => ({
                  label,
                  href: getExternalUrl(label, value, data.media_type),
                }))
                .filter((item): item is { label: string; href: string } => item.href !== null);
              if (linkItems.length === 0) return null;
              return (
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {linkItems.map(({ label, href }) => (
                    <a
                      key={label}
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm font-medium text-[#2a2520]/65 hover:text-[#96551d] transition-colors rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#96551d]/50"
                    >
                      <ExternalLink size={14} />
                      {label}
                    </a>
                  ))}
                </div>
              );
            })()}

            {data.genres.length > 0 && (
              <div className="flex flex-wrap gap-x-2 gap-y-1">
                {data.genres.map((genre) => (
                  <span key={genre} className="text-xs px-3 py-1 rounded-full bg-[#c9b89a]/30 text-[#2a2520]/80 font-medium">
                    {genre}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {data.overview && (
        <div className="flex flex-col gap-2 max-w-3xl">
          <h2 className="text-base font-semibold text-[#2a2520]/75 uppercase tracking-wide">
            Overview
          </h2>
          <p className="text-base text-[#2a2520]/80 leading-relaxed">{data.overview}</p>
        </div>
      )}
    </div>
  );
}
