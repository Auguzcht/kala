import { create } from "zustand";

// EPHEMERAL UI STATE ONLY. Never put server data here (use TanStack Query),
// and never put auth here (that is the session).
interface UIState {
  activeCourseTab: string;
  commandOpen: boolean;
  /** Active cross-page tour step (0-based), null when no tour is running.
   * Ephemeral UI state: lives here so any course page can read it, and so a
   * route change (which remounts pages but not the CourseShell layout) does
   * not lose where the tour is. */
  tourStep: number | null;
  setTab: (tab: string) => void;
  setCommandOpen: (open: boolean) => void;
  setTourStep: (step: number | null) => void;
}

export const useUI = create<UIState>((set) => ({
  activeCourseTab: "overview",
  commandOpen: false,
  tourStep: null,
  setTab: (activeCourseTab) => set({ activeCourseTab }),
  setCommandOpen: (commandOpen) => set({ commandOpen }),
  setTourStep: (tourStep) => set({ tourStep }),
}));
