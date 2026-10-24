import { useCallback, useEffect, useState } from "react";
import {
  clampTutorHistoryWidth,
  TUTOR_HISTORY_DEFAULT,
  tutorHistoryMaxWidth,
} from "@/features/tutor/lib/history-width";

/** Tutor-only layout state; other course routes do not subscribe to resize. */
export function useTutorHistoryWidth(enabled: boolean) {
  const [width, setWidth] = useState(TUTOR_HISTORY_DEFAULT);
  const [viewport, setViewport] = useState(() => window.innerWidth);
  useEffect(() => {
    if (!enabled) return;
    const resize = () => {
      setViewport(window.innerWidth);
      if (window.innerWidth >= 1024)
        setWidth((current) =>
          clampTutorHistoryWidth(current, window.innerWidth),
        );
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [enabled]);
  const changeWidth = useCallback((next: number) => {
    setWidth(clampTutorHistoryWidth(next, window.innerWidth));
  }, []);
  return { width, maxWidth: tutorHistoryMaxWidth(viewport), changeWidth };
}
