import { Check, Loader2 } from "lucide-react";

interface EpisodeStatusToggleProps {
  watched: boolean;
  isManual: boolean;
  isLoading?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

function getTitle(watched: boolean, isManual: boolean, disabled?: boolean): string {
  if (disabled) return "Select a Jellyfin user first";
  if (!watched && !isManual) return "Mark as watched";
  if (!watched && isManual) return "Unwatched · marked manually";
  if (watched && !isManual) return "Watched · synced from Jellyfin";
  return "Watched · marked manually";
}

export function EpisodeStatusToggle({
  watched,
  isManual,
  isLoading = false,
  disabled = false,
  onClick,
}: EpisodeStatusToggleProps) {
  const title = getTitle(watched, isManual, disabled);

  const hoverClass = !disabled ? "hover:ring-2 hover:ring-mt-cta/50 hover:ring-offset-1" : "";
  const disabledClass = disabled ? "opacity-50 cursor-not-allowed" : "";

  let circleClass: string;
  if (watched) {
    circleClass = `bg-mt-cta rounded-full w-5 h-5 flex items-center justify-center ${hoverClass}`;
  } else {
    circleClass = `border-2 border-[#2a2520]/30 rounded-full w-5 h-5 flex items-center justify-center ${hoverClass}`;
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={watched}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`relative flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/60 rounded-full transition-all ${disabledClass}`}
    >
      <span className={circleClass}>
        {isLoading ? (
          <Loader2 size={12} className="animate-spin text-[#2a2520]/50" />
        ) : watched ? (
          <Check size={12} className="text-[#2a2520]" />
        ) : null}
      </span>
      {isManual && !isLoading && (
        <span
          className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-[#96551d] ring-1 ring-white"
          aria-hidden="true"
        />
      )}
    </button>
  );
}
