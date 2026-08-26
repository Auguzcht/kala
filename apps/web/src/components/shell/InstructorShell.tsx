import { useState, type ReactNode } from "react";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import { TopBar } from "@/components/shell/TopBar";

// Instructor shell: top bar + first-launch tour banner (per the mockup
// "Instructor Dashboard"). The tour is the brief's named onboarding
// mechanism (Driver.js) and doubles as the conference demo walkthrough:
// heatmap → needs-support list → a student's twin.

const TOUR_KEY = "kala.instructor.tour";

const tourSteps = [
  {
    element: "#heatmap-panel",
    popover: {
      title: "Skills × Bloom's mastery",
      description:
        "Cohort and per-student mastery across skills, grouped by Bloom's level. Cells pair color with a letter — never color alone.",
    },
  },
  {
    element: "#at-risk-list",
    popover: {
      title: "Needs support",
      description:
        "Evidence-triggered flags with their reasons. Supportive wording, never a verdict on a student.",
    },
  },
  {
    element: "#cohort-readiness",
    popover: {
      title: "Cohort readiness",
      description:
        "A heuristic rollup from evidence to date, weighted to the blueprint — not a grade prediction.",
    },
  },
];

export function InstructorShell({
  courseId,
  displayName,
  children,
}: {
  courseId: string;
  displayName?: string;
  children: ReactNode;
}) {
  const [showTour, setShowTour] = useState(
    () => localStorage.getItem(TOUR_KEY) !== "dismissed"
  );

  const dismissTour = () => {
    localStorage.setItem(TOUR_KEY, "dismissed");
    setShowTour(false);
  };

  const startTour = () => {
    const instance = driver({ showProgress: true, steps: tourSteps, overlayColor: "rgba(14,27,51,0.35)" });
    instance.drive();
  };

  const initials = (displayName ?? "")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  return (
    <div className="min-h-dvh bg-background">
      <TopBar
        courseId={courseId}
        section="Instructor dashboard"
        right={
          initials ? (
            <span className="grid size-6.5 place-items-center rounded-full bg-brand-slate text-[10px] font-semibold text-background">
              {initials}
            </span>
          ) : null
        }
      />

      {showTour ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-brand-orange/20 bg-brand-orange/8 px-6 py-2.5">
          <span className="text-xs font-semibold text-brand-orange-foreground">
            First time here?
          </span>
          <span className="text-xs text-muted-foreground">
            Take the 60-second tour — heatmap, needs-support list, then a student's twin.
          </span>
          <div className="flex-1" />
          <button
            type="button"
            onClick={startTour}
            className="rounded-[3px] bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
          >
            Take the tour
          </button>
          <button
            type="button"
            onClick={dismissTour}
            className="rounded-[3px] border border-primary/20 px-3 py-1 text-xs font-semibold text-foreground hover:bg-accent"
          >
            Got it
          </button>
        </div>
      ) : null}

      <main className="w-full px-6 py-7">{children}</main>
    </div>
  );
}
