import type { MediaType } from "../../types/media";

interface Props {
  type?: MediaType;
  total: number;
}

const TITLES: Record<string, { title: string; subtitle: string; itemLabel: string }> = {
  movie:  { title: "Movies",    subtitle: "Your movie collection",                     itemLabel: "movies" },
  series: { title: "Series",    subtitle: "Your series collection",                    itemLabel: "series" },
  all:    { title: "All Media", subtitle: "Track your movies and series in one place", itemLabel: "items"  },
};

export function MediaListHeader({ type, total }: Props) {
  const key = type ?? "all";
  const { title, subtitle, itemLabel } = TITLES[key];
  return (
    <div>
      <h1 className="text-2xl font-bold text-[#2a2520]">{title}</h1>
      <p className="text-sm text-[#2a2520]/70">{subtitle}</p>
      <p className="text-sm text-[#2a2520]/70 mt-1">{total} {itemLabel}</p>
    </div>
  );
}
