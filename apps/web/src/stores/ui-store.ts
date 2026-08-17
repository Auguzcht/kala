import { create } from "zustand";

// EPHEMERAL UI STATE ONLY. Never put server data here (use TanStack Query),
// and never put auth here (that is the session).
interface UIState {
  activeCourseTab: string;
  commandOpen: boolean;
  setTab: (tab: string) => void;
  setCommandOpen: (open: boolean) => void;
}

export const useUI = create<UIState>((set) => ({
  activeCourseTab: "overview",
  commandOpen: false,
  setTab: (activeCourseTab) => set({ activeCourseTab }),
  setCommandOpen: (commandOpen) => set({ commandOpen }),
}));
