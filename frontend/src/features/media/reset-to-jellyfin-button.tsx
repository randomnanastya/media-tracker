import { Loader2, RotateCcw } from "lucide-react";

interface ResetToJellyfinButtonProps {
  isManual: boolean;
  isLoading?: boolean;
  onClick: () => void;
}

export function ResetToJellyfinButton({ isManual, isLoading, onClick }: ResetToJellyfinButtonProps) {
  if (!isManual) return <div className="w-4 h-4 shrink-0" aria-hidden="true" />;

  return (
    <button
      type="button"
      aria-label="Reset to Jellyfin"
      title="Reset to Jellyfin"
      onClick={onClick}
      className="shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb826]/50 rounded text-[#2a2520]/40 hover:text-[#2a2520]/80 transition-colors"
    >
      {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RotateCcw size={16} />}
    </button>
  );
}
