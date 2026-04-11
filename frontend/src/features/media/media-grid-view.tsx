import type { MediaItem } from "../../types/media";
import { MediaGridCard } from "./media-grid-card";

interface Props {
  items: MediaItem[];
}

export function MediaGridView({ items }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-4">
      {items.map((item) => (
        <MediaGridCard key={item.id} item={item} />
      ))}
    </div>
  );
}
