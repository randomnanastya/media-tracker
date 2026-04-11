import { LayoutGrid, List } from "lucide-react";
import type { ViewMode } from "../../types/media";

interface Props {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export function MediaViewToggle({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-1">
      {(["list", "grid"] as const).map((mode) => {
        const Icon = mode === "list" ? List : LayoutGrid;
        const isActive = value === mode;
        return (
          <button
            key={mode}
            type="button"
            aria-label={mode === "list" ? "List view" : "Grid view"}
            onClick={() => onChange(mode)}
            className={`p-2 rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-[#ffb826] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F5ECD7] ${
              isActive
                ? "bg-[#ffb826]/15 text-[#8B6914]"
                : "text-[#2a2520]/55 hover:text-[#2a2520]/70"
            }`}
          >
            <Icon size={18} />
          </button>
        );
      })}
    </div>
  );
}
