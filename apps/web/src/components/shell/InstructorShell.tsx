import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "@tanstack/react-router";
import "driver.js/dist/driver.css";
import { TopBar } from "@/components/shell/TopBar";
import { InstructorTourRunner } from "@/components/shell/InstructorTour";
import {
  INSTRUCTOR_TOUR_STEPS,
  instructorTourDismissKey,
} from "@/components/shell/instructor-tour";
import { CompassIcon, type CompassIconHandle } from "@/components/ui/compass";
import { useLearnerRecord } from "@/features/instructor";
import { useUI } from "@/stores/ui-store";
import { useSession } from "@/lib/auth/AuthProvider";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// Instructor shell: top bar + first-launch tour banner + the cross-page
// tour runner (mirrors CourseShell's student side). The tour is the
// brief's named onboarding mechanism (Driver.js) and doubles as the
// conference demo walkthrough: KPI strip → roster → triage sheet → needs
// support → trends → heatmap → one learner's record. The banner shows on
// the overview only (the record page's anchors don't all exist there), but
// the runner itself is mounted for every /class route so the walkthrough
// can cross into the learner record.

const STUDENT_ROUTE = /^\/class\/student\/([^/]+)/;

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
  const navigate = useNavigate();
  const session = useSession();
  const tourKey = session?.userId ? instructorTourDismissKey(session.userId) : null;
  const [tourPrompted, setTourPrompted] = useState(
    () => (tourKey ? localStorage.getItem(tourKey) !== "dismissed" : false)
  );
  const [confirmOpen, setConfirmOpen] = useState(false);

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

  // The tour's anchors (#tour-cohort-kpis, #roster-panel, #at-risk-list,
  // #cohort-analytics, #heatmap-panel) only exist on the overview. The
  // banner reads tourStep so it hides when the walkthrough completes even
  // without a remount (the runner writes the same "dismissed" key).
  const onOverview = pathname === "/class" || pathname === "/class/";
  const tourStep = useUI((s) => s.tourStep);
  useEffect(() => {
    if (tourStep === null && tourKey) {
      setTourPrompted(localStorage.getItem(tourKey) !== "dismissed");
    }
  }, [tourStep, tourKey]);

  const dismissTour = () => {
    if (tourKey) localStorage.setItem(tourKey, "dismissed");
    setTourPrompted(false);
  };

  // Confirmation before the walkthrough fires (pre-tour dialog, not a
  // drive-into-the-user) — same as the student workspace.
  const confirmStart = () => setConfirmOpen(true);

  const startTour = () => {
    setConfirmOpen(false);
    useUI.getState().setTourStep(0);
    // The tour starts on the class overview; starting it from the learner
    // record needs a navigation, same as the student side.
    if (pathname !== INSTRUCTOR_TOUR_STEPS[0].route) {
      void navigate({ to: INSTRUCTOR_TOUR_STEPS[0].route });
    }
  };

  const bannerVisible = tourPrompted && onOverview;

  // The tour icon is the animated compass (lucide-animated registry, same
  // source as the other ui icons): the needle turns when the BUTTON is
  // hovered (controlled-mode handlers), same pattern as the decision
  // buttons. A compass for "take the tour" — orientation, not the AI mark.
  const tourIconRef = useRef<CompassIconHandle | null>(null);
  const iconPlay = () => tourIconRef.current?.startAnimation();
  const iconStop = () => tourIconRef.current?.stopAnimation();

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
          <div className="flex items-center gap-2">
            {/* One affordance, always: the quiet compass nav button. The
                banner is the loud CTA when it is up; off-overview there is
                no banner, so the icon carries it. */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={confirmStart}
                  onMouseEnter={iconPlay}
                  onMouseLeave={iconStop}
                  aria-label="Take the tour"
                  className="grid size-7 place-items-center rounded-[3px] text-muted-foreground/70 hover:bg-accent hover:text-foreground"
                >
                  <CompassIcon ref={tourIconRef} size={15} aria-hidden />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Take the tour</TooltipContent>
            </Tooltip>
            {initials ? (
              <span className="grid size-6.5 place-items-center rounded-full bg-brand-slate text-[10px] font-semibold text-background">
                {initials}
              </span>
            ) : null}
          </div>
        }
      />

      {bannerVisible ? (
        <div className="flex flex-wrap items-center gap-3 border-b border-brand-orange/20 bg-brand-orange/8 px-6 py-2.5">
          <span className="text-xs font-semibold text-brand-orange-foreground">
            First time here?
          </span>
          <span className="text-xs text-muted-foreground">
            Take the 90-second tour: your roster, who needs support, the charts, then one learner's
            record.
          </span>
          <div className="flex-1" />
          <button
            type="button"
            onClick={confirmStart}
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

      {/* Cross-page runner — mounted for every /class route, owns the
          walkthrough across overview + learner record. */}
      {/* Pre-tour confirmation, same as the student workspace. */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Take the tour?</DialogTitle>
            <DialogDescription>
              About 2 minutes — roster, triage sheet, charts, then one learner's record. You can exit anytime.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button
              type="button"
              onClick={() => setConfirmOpen(false)}
              className="rounded-[3px] border border-primary/20 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-accent"
            >
              Maybe later
            </button>
            <button
              type="button"
              onClick={startTour}
              className="rounded-[3px] bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Start tour
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <InstructorTourRunner />
    </div>
  );
}
