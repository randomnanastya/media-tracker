import { LayoutGrid, List } from "lucide-react";
import type { ViewMode } from "../../types/media";

interface Props {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export function MediaViewToggle({ value, onChange }: Props) {
  return (
    <div className="flex items-center border border-[#c9b89a]/40 rounded-lg bg-white shadow-sm overflow-hidden">
      {(["list", "grid"] as const).map((mode) => {
        const Icon = mode === "list" ? List : LayoutGrid;
        const isActive = value === mode;
        return (
          <button
            key={mode}
            type="button"
            aria-label={mode === "list" ? "List view" : "Grid view"}
            onClick={() => onChange(mode)}
            className={`p-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#ffb826] ${
              isActive
                ? "bg-[#ffb826]/15 text-[#8B6914]"
                : "text-[#2a2520]/55 hover:text-[#2a2520]/70 hover:bg-[#2a2520]/5"
            }`}
          >
            <Icon size={18} />
          </button>
        );
      })}
    </div>
  );
}
