import type { MediaItem } from "../../types/media";
import { MediaListCard } from "./media-list-card";

interface Props {
  items: MediaItem[];
}

export function MediaListView({ items }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => (
        <MediaListCard key={item.id} item={item} />
      ))}
    </div>
  );
}
