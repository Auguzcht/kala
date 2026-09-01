import { useState, type ReactNode } from "react";
import { useLocation } from "@tanstack/react-router";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import { TopBar } from "@/components/shell/TopBar";
import { useLearnerRecord } from "@/features/instructor";

// Instructor shell: top bar + first-launch tour banner (per the mockup
// "Instructor Dashboard"). The tour is the brief's named onboarding
// mechanism (Driver.js) and doubles as the conference demo walkthrough:
// roster → needs-support list → cohort trends → one learner's record.

const TOUR_KEY = "kala.instructor.tour";
const STUDENT_ROUTE = /^\/class\/student\/([^/]+)/;

const tourSteps = [
  {
    element: "#roster-panel",
    popover: {
      title: "Your class, triaged",
      description:
        "Every enrolled student, sorted by who needs you first. Real names, because you are the teacher of record. Flip the de-identify switch to show pseudonyms when you are screen-sharing.",
    },
  },
  {
    element: "#at-risk-list",
    popover: {
      title: "Needs support",
      description:
        "Evidence-triggered flags with the specific reason behind each one. Supportive wording, never a verdict on a student.",
    },
  },
  {
    element: "#cohort-analytics",
    popover: {
      title: "Is the class moving?",
      description:
        "Readiness over time, practice volume, mastery mix, and the weakest skills across the class — the reteach list.",
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
  const { pathname } = useLocation();
  const [showTour, setShowTour] = useState(
    () => localStorage.getItem(TOUR_KEY) !== "dismissed"
  );

  // This shell renders once for every route under /class via <Outlet/>, so
  // the breadcrumb was stuck on a single hardcoded "Instructor dashboard"
  // no matter which page was actually open — the class overview and one
  // learner's record looked identical in the crumb. Resolve a subsection
  // from the path the same way CourseShell already does for the student
  // side (SECTION_LABELS keyed on pathname); the one difference is the
  // learner route is dynamic, so its label comes from a name lookup rather
  // than a static table.
  const studentMatch = pathname.match(STUDENT_ROUTE);
  const studentUid = studentMatch?.[1];
  // Same query key LearnerRecord itself uses, so this is a cache hit (or a
  // request already in flight) rather than a second network call — the
  // page below is fetching the identical data for its own header.
  const learner = useLearnerRecord(courseId, studentUid ?? "");
  const subsection = studentUid
    ? learner.data?.displayName ?? "Learner record"
    : undefined;

  // The tour's anchors (#roster-panel, #at-risk-list, #cohort-analytics)
  // only exist on the overview. Showing the banner on a learner's record
  // page would offer a tour that highlights nothing.
  const onOverview = pathname === "/class" || pathname === "/class/";

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
        subsection={subsection}
        right={
          initials ? (
            <span className="grid size-6.5 place-items-center rounded-full bg-brand-slate text-[10px] font-semibold text-background">
              {initials}
            </span>
          ) : null
        }
      />

      {showTour && onOverview ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-brand-orange/20 bg-brand-orange/8 px-6 py-2.5">
          <span className="text-xs font-semibold text-brand-orange-foreground">
            First time here?
          </span>
          <span className="text-xs text-muted-foreground">
            Take the 60-second tour: your roster, who needs support, then how the class is moving.
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
