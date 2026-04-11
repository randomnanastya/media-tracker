import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
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
        className="flex items-center gap-2 px-3 py-2 bg-white border border-[#c9b89a]/30 rounded-lg shadow-sm text-sm text-[#2a2520] focus-visible:ring-2 focus-visible:ring-[#ffb826] focus-visible:ring-offset-2"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selected.label}
        <ChevronDown size={14} />
      </button>
      {open && (
        <ul
          role="listbox"
          className="absolute right-0 mt-1 w-40 bg-white border border-[#c9b89a]/30 rounded-lg shadow-sm z-10 py-1"
        >
          {OPTIONS.map((opt) => (
            <li
              key={opt.value ?? "all"}
              role="option"
              aria-selected={opt.value === value}
              className="px-3 py-2 text-sm text-[#2a2520] cursor-pointer hover:bg-[#ffb826]/10 focus-visible:bg-[#ffb826]/10 focus-visible:outline-none"
              onClick={() => { onChange(opt.value); setOpen(false); }}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { onChange(opt.value); setOpen(false); } }}
              tabIndex={0}
            >
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
