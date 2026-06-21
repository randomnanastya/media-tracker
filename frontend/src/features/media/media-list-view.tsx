import type { MediaItem } from "../../types/media";
import { MediaListCard } from "./media-list-card";

interface Props {
  items: MediaItem[];
  from?: string;
}

export function MediaListView({ items, from }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => (
        <MediaListCard key={item.id} item={item} from={from} />
      ))}
    </div>
  );
}
