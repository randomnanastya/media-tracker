import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import type { WatchStatus } from "../../types/media";

interface Props {
  value: WatchStatus | null;
  onChange: (value: WatchStatus | null) => void;
}

const OPTIONS: { label: string; value: WatchStatus | null }[] = [
  { label: "All Status", value: null },
  { label: "Watched", value: "watched" },
  { label: "Watching", value: "watching" },
  { label: "Planned", value: "planned" },
  { label: "Dropped", value: "dropped" },
];

export function MediaStatusFilter({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const selected = OPTIONS.find((o) => o.value === value) ?? OPTIONS[0];

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 min-w-[160px] bg-white border border-[#c9b89a]/40 rounded-lg shadow-sm text-sm text-[#2a2520] focus-visible:ring-2 focus-visible:ring-[#ffb826] focus-visible:ring-offset-2"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="flex-1 text-left">{selected.label}</span>
        <ChevronDown size={14} className="shrink-0 text-[#2a2520]/50" />
      </button>
      {open && (
        <ul
          role="listbox"
          className="absolute right-0 mt-1 min-w-[160px] bg-white border border-[#c9b89a]/40 rounded-lg shadow-md z-10 py-1"
        >
          {OPTIONS.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <li
                key={opt.value ?? "all"}
                role="option"
                aria-selected={isSelected}
                className={`flex items-center justify-between px-3 py-2 text-sm cursor-pointer focus-visible:outline-none ${
                  isSelected
                    ? "bg-[#ffb826]/10 text-[#7a5c10] font-medium"
                    : "text-[#2a2520] hover:bg-[#ffb826]/10"
                }`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { onChange(opt.value); setOpen(false); } }}
                tabIndex={0}
              >
                <span>{opt.label}</span>
                {isSelected && <Check size={14} className="text-[#7a5c10]" />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
