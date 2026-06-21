import { useState, useRef, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal } from "lucide-react";
import { mediaApi } from "../../api/media";
import { useJellyfinUser } from "../../contexts/jellyfin-user-context";
import { ConfirmDialog } from "../../components/confirm-dialog";

interface MediaActionsMenuProps {
  mediaId: number;
  mediaType: "movie" | "series";
  isManual: boolean;
}

type ConfirmActionType = "watched" | "watching" | "dropped" | "planned" | "reset";

const DIALOG_CONFIG: Record<ConfirmActionType, { title: string; description: string; confirmLabel: string }> = {
  watched: {
    title: "Mark as watched",
    description: "Mark entire series as watched for all episodes?",
    confirmLabel: "Mark watched",
  },
  watching: {
    title: "Mark as watching",
    description: "Mark entire series as currently watching for all episodes?",
    confirmLabel: "Mark watching",
  },
  dropped: {
    title: "Mark as dropped",
    description: "Mark entire series as dropped for all episodes?",
    confirmLabel: "Mark dropped",
  },
  planned: {
    title: "Mark as unwatched",
    description: "Mark entire series as unwatched for all episodes?",
    confirmLabel: "Mark unwatched",
  },
  reset: {
    title: "Reset to Jellyfin",
    description: "Remove all manual watch statuses? Jellyfin data will be restored on next sync.",
    confirmLabel: "Reset",
  },
};

export function MediaActionsMenu({ mediaId, mediaType, isManual }: MediaActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionType | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstMenuItemRef = useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();
  const { selectedUser } = useJellyfinUser();

  const jellyfinUserId = selectedUser?.jellyfin_user_id ?? "";
  const canAct = !!jellyfinUserId;

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (isOpen) {
      firstMenuItemRef.current?.focus();
    } else {
      triggerRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
        return;
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = menuRef.current
          ? Array.from(menuRef.current.querySelectorAll<HTMLButtonElement>('[role="menuitem"]'))
          : [];
        if (items.length === 0) return;
        const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
        let nextIndex: number;
        if (e.key === "ArrowDown") {
          nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        } else {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        items[nextIndex]?.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const mutation = useMutation<void, Error, ConfirmActionType>({
    mutationFn: async (action: ConfirmActionType) => {
      if (!canAct) throw new Error("No Jellyfin user");
      if (action === "watched") {
        await mediaApi.setSeriesWatchStatus(mediaId, "watched", jellyfinUserId);
      } else if (action === "watching") {
        await mediaApi.setSeriesWatchStatus(mediaId, "watching", jellyfinUserId);
      } else if (action === "dropped") {
        await mediaApi.setSeriesWatchStatus(mediaId, "dropped", jellyfinUserId);
      } else if (action === "planned") {
        await mediaApi.setSeriesWatchStatus(mediaId, "planned", jellyfinUserId);
      } else if (mediaType === "series") {
        await mediaApi.clearSeriesManual(mediaId, jellyfinUserId);
      } else {
        await mediaApi.clearMovieManual(mediaId, jellyfinUserId);
      }
    },
    onSuccess: () => {
      setConfirmAction(null);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["media", mediaId] });
    },
  });

  if (mediaType === "movie" && !isManual) {
    return null;
  }

  const menuItemClass = "w-full text-left px-4 py-2 text-sm hover:bg-[#f5f0e8] transition-colors";

  function handleMenuItemClick(action: ConfirmActionType) {
    setIsOpen(false);
    setConfirmAction(action);
  }

  const activeConfig = confirmAction ? DIALOG_CONFIG[confirmAction] : null;

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label="Media actions"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(true)}
        className="p-1.5 rounded-lg hover:bg-[#2a2520]/10 text-[#2a2520]/60 hover:text-[#2a2520] transition-colors"
      >
        <MoreHorizontal size={18} />
      </button>

      {isOpen && (
        <div
          ref={menuRef}
          role="menu"
          className="absolute right-0 top-full mt-1 z-20 bg-white shadow-lg rounded-xl border border-[#c9b89a]/30 py-1 min-w-[220px]"
        >
          {mediaType === "series" && (
            <>
              <button
                ref={firstMenuItemRef}
                type="button"
                role="menuitem"
                className={menuItemClass}
                onClick={() => handleMenuItemClick("watched")}
              >
                Mark entire series as watched
              </button>
              <button
                type="button"
                role="menuitem"
                className={menuItemClass}
                onClick={() => handleMenuItemClick("watching")}
              >
                Mark entire series as watching
              </button>
              <button
                type="button"
                role="menuitem"
                className={menuItemClass}
                onClick={() => handleMenuItemClick("dropped")}
              >
                Mark entire series as dropped
              </button>
              <button
                type="button"
                role="menuitem"
                className={menuItemClass}
                onClick={() => handleMenuItemClick("planned")}
              >
                Mark entire series as unwatched
              </button>
              {isManual && (
                <>
                  <hr className="my-1 border-[#c9b89a]/30" />
                  <button
                    type="button"
                    role="menuitem"
                    className={`${menuItemClass} text-[#96551d]`}
                    onClick={() => handleMenuItemClick("reset")}
                  >
                    Reset all to Jellyfin
                  </button>
                </>
              )}
            </>
          )}

          {mediaType === "movie" && isManual && (
            <button
              ref={firstMenuItemRef}
              type="button"
              role="menuitem"
              className={`${menuItemClass} text-[#96551d]`}
              onClick={() => handleMenuItemClick("reset")}
            >
              Reset to Jellyfin
            </button>
          )}
        </div>
      )}

      {activeConfig && (
        <ConfirmDialog
          open={confirmAction !== null}
          title={activeConfig.title}
          description={activeConfig.description}
          confirmLabel={activeConfig.confirmLabel}
          onConfirm={() => confirmAction && mutation.mutate(confirmAction)}
          onCancel={() => setConfirmAction(null)}
          isLoading={mutation.isPending}
        />
      )}
    </div>
  );
}
