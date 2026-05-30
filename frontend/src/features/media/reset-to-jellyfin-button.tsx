import { Loader2, RotateCcw } from "lucide-react";

interface ResetToJellyfinButtonProps {
  isManual: boolean;
  isLoading?: boolean;
  onClick: () => void;
}

export function ResetToJellyfinButton({ isManual, isLoading, onClick }: ResetToJellyfinButtonProps) {
  if (!isManual) return null;

  return (
    <button
      type="button"
      aria-label="Reset to Jellyfin"
      title="Reset to Jellyfin"
      onClick={onClick}
      className="pointer-coarse:opacity-60 sm:opacity-0 sm:group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/50 rounded text-[#2a2520]/40 hover:text-[#2a2520]/80 transition-all"
    >
      {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
    </button>
  );
}
