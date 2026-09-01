import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import {
  useEffect,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
  type Ref,
} from "react";
import { CompassIcon, type CompassIconHandle } from "@/components/ui/compass";
import { useSession } from "@/lib/auth/AuthProvider";
import { ActivityIcon } from "@/components/ui/activity";
import { FileTextIcon } from "@/components/ui/file-text";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { LayersIcon } from "@/components/ui/layers";
import { LayoutGridIcon } from "@/components/ui/layout-grid";
import { MessageSquareIcon } from "@/components/ui/message-square";
import { ZapIcon } from "@/components/ui/zap";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TopBar } from "@/components/shell/TopBar";
import { GamificationSummary } from "@/features/gamification";
import { TourStepRunner } from "@/components/shell/StudentTour";
import {
  TOUR_STEPS,
  studentTourDismissKey,
} from "@/components/shell/student-tour";
import { useUI } from "@/stores/ui-store";

// App shell for the course-scoped (LTI) surface. 56px icon side rail +
// 48px top bar, per the mockups ("App Side Rail", "App Top Bar"):
// hairline slate borders, white chrome, orange active accent.
// The shell is the instrument frame; pages render inside it.

// Animated lucide icons (lucide-animated): hover-triggered by default, so
// the rail icons draw on hover and on route activation — motion tied to the
// cursor and the active state, never looping. Passing a ref switches each
// icon to CONTROLLED mode (its isControlledRef gate disables the hover
// trigger), and the shell drives startAnimation/stopAnimation from the
// active route instead — animate on selection, not on hover.
type NavIconHandle = { startAnimation: () => void; stopAnimation: () => void };
type NavIcon = ComponentType<{ size?: number; className?: string } & { ref?: Ref<NavIconHandle> }>;

const NAV: { to: string; label: string; icon: NavIcon; end?: boolean; anchorId: string }[] = [
  { to: "/course", label: "Workspace", icon: LayoutGridIcon, end: true, anchorId: "nav-workspace" },
  { to: "/course/diagnostic", label: "Diagnostic", icon: FileTextIcon, anchorId: "nav-diagnostic" },
  { to: "/course/lessons", label: "Lessons", icon: GraduationCapIcon, anchorId: "nav-lessons" },
  { to: "/course/practice", label: "Practice", icon: ZapIcon, anchorId: "nav-practice" },
  { to: "/course/flashcards", label: "Flashcards", icon: LayersIcon, anchorId: "nav-flashcards" },
  { to: "/course/tutor", label: "Tutor", icon: MessageSquareIcon, anchorId: "nav-tutor" },
  { to: "/course/twin", label: "Twin", icon: ActivityIcon, anchorId: "nav-twin" },
];

const SECTION_LABELS: Record<string, string> = {
  "/course": "Workspace",
  "/course/diagnostic": "Diagnostic",
  "/course/lessons": "Lessons",
  "/course/practice": "Practice",
  "/course/flashcards": "Flashcards",
  "/course/tutor": "Tutor",
  "/course/twin": "Twin",
};

function initials(name?: string): string {
  if (!name) return "";
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

export function CourseShell({
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
  const section = SECTION_LABELS[pathname] ?? SECTION_LABELS["/course"];

  // One ref per rail icon; the active route's icon animates, the rest are
  // stopped. Passing a ref is what disables each icon's own hover trigger.
  const iconHandles = useRef<(NavIconHandle | null)[]>([]);
  useEffect(() => {
    const idx = NAV.findIndex((n) => (n.end ? pathname === n.to : pathname.startsWith(n.to)));
    iconHandles.current.forEach((h, i) => {
      if (!h) return;
      if (i === idx) h.startAnimation();
      else h.stopAnimation();
    });
  }, [pathname]);

  // One loud prompt before the tour has ever been taken or dismissed: the
  // workspace banner. After "Got it" or completing the walkthrough the
  // banner is gone permanently and the TopBar affordance shrinks to a quiet
  // icon — never both loud at once. Per-user key (unlike the instructor
  // tour's global one): each student's state is theirs alone.
  const tourKey = session?.userId ? studentTourDismissKey(session.userId) : null;
  const [tourPrompted, setTourPrompted] = useState(
    () => (tourKey ? localStorage.getItem(tourKey) !== "dismissed" : false)
  );
  const [confirmOpen, setConfirmOpen] = useState(false);

  // The tour's completion path writes the same "dismissed" key as "Got it"
  // (see TourStepRunner) — re-read it when the store goes back to idle so
  // the banner hides without a remount.
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
  // drive-into-the-user).
  const confirmStart = () => setConfirmOpen(true);

  // The tour icon is the animated compass (lucide-animated registry,
  // same source as the other ui icons): the needle turns when the BUTTON
  // is hovered (controlled-mode handlers), same pattern as the instructor
  // shell's tour button.
  const tourIconRef = useRef<CompassIconHandle | null>(null);
  const iconPlay = () => tourIconRef.current?.startAnimation();
  const iconStop = () => tourIconRef.current?.stopAnimation();

  const startTour = () => {
    setConfirmOpen(false);
    useUI.getState().setTourStep(0);
    if (pathname !== TOUR_STEPS[0].route) {
      void navigate({ to: TOUR_STEPS[0].route });
    }
  };

  const bannerVisible = tourPrompted && pathname === "/course";

  return (
    <div className="min-h-dvh bg-background">
      <TourStepRunner />

      {/* Side rail */}
      <nav
        aria-label="Course"
        className="fixed inset-y-0 left-0 z-20 flex w-14 flex-col items-center border-r bg-card px-0 py-4"
      >
        <Link to="/course" className="mb-5">
          <img
            src="/Kala-Logo.png"
            alt="Kala"
            className="h-6 w-6 object-contain"
          />
        </Link>
        <div className="flex flex-1 flex-col gap-1.5">
          {NAV.map(({ to, label, icon: Icon, end, anchorId }, i) => (
            <Tooltip key={to}>
              <TooltipTrigger asChild>
                <Link
                  to={to}
                  id={anchorId}
                  activeOptions={{ exact: end }}
                  activeProps={{
                    className:
                      "flex h-9 w-9 items-center justify-center border-l-2 border-brand-orange bg-brand-orange/10 text-brand-orange",
                  }}
                  inactiveProps={{
                    className:
                      "flex h-9 w-9 items-center justify-center border-l-2 border-transparent text-muted-foreground/70 hover:bg-accent hover:text-foreground",
                  }}
                  aria-label={label}
                >
                  <Icon
                    size={18}
                    ref={(h) => {
                      iconHandles.current[i] = h ?? null;
                    }}
                  />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          ))}
        </div>
        <div
          className="grid size-7 place-items-center rounded-full bg-brand-slate text-[10px] font-semibold text-background"
          title={displayName}
        >
          {initials(displayName)}
        </div>
      </nav>

      {/* Content column */}
      <div className="pl-14">
        <TopBar
          courseId={courseId}
          section={section}
          right={
            <div className="flex items-center gap-4">
              <GamificationSummary courseId={courseId} />
              {bannerVisible ? (
                // Quiet icon while the banner carries the loud CTA.
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
              ) : tourPrompted ? (
                // Never taken/dismissed but not on the workspace: full-text.
                <button
                  type="button"
                  onClick={confirmStart}
                  className="rounded-[3px] border border-primary/20 px-2.5 py-1 text-xs font-semibold text-foreground hover:bg-accent"
                >
                  Take the tour
                </button>
              ) : (
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
              )}
              <span className="font-mono text-xs text-muted-foreground">
                {initials(displayName) || section}
              </span>
            </div>
          }
        />

        {bannerVisible ? (
          <div className="flex flex-wrap items-center gap-3 border-b border-brand-orange/20 bg-brand-orange/8 px-6 py-2.5">
            <span className="text-xs font-semibold text-brand-orange-foreground">
              First time here?
            </span>
            <span className="text-xs text-muted-foreground">
              Take a short tour — diagnostic, lessons, practice, tutor, then your twin.
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

        <main className="mx-auto max-w-screen-2xl px-6 py-8 pb-24 lg:px-10">{children}</main>
      </div>

      {/* Pre-tour confirmation */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Take the tour?</DialogTitle>
            <DialogDescription>
              About 2–3 minutes. You can exit anytime.
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
    </div>
  );
}
