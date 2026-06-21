import { useEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router";

const SCROLL_CONTAINER_ID = "main-scroll";

export function saveScrollPosition(key: string) {
  const el = document.getElementById(SCROLL_CONTAINER_ID);
  if (el) {
    sessionStorage.setItem(`scroll:${key}`, String(el.scrollTop));
  }
}

export function useScrollRestore(key: string, ready: boolean = true) {
  const navigationType = useNavigationType();
  const location = useLocation();

  const shouldRestore =
    navigationType === "POP" ||
    (location.state as Record<string, unknown> | null)?.scrollRestore === true;

  const restoredRef = useRef(false);

  useEffect(() => {
    if (!shouldRestore || !ready || restoredRef.current) return;

    const saved = sessionStorage.getItem(`scroll:${key}`);
    if (saved === null) return;

    const el = document.getElementById(SCROLL_CONTAINER_ID);
    if (!el) return;

    restoredRef.current = true;
    el.scrollTop = parseInt(saved, 10);
  }, [key, shouldRestore, ready]);
}
