import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/spinner";
import { fetchBankStatus } from "@/features/bank/api/bank.api";
import { fetchPracticeSets } from "@/features/practice/api/practice.api";
import type { Lesson } from "@/features/lessons/schema/lessons.schema";
import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import {
  useEffect,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
  type ReactNode,
  type Ref,
} from "react";
import { CompassIcon, type CompassIconHandle } from "@/components/ui/compass";
import { useSession } from "@/lib/auth/AuthProvider";
import { ActivityIcon } from "@/components/ui/activity";
import { FileTextIcon } from "@/components/ui/file-text";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { LayoutGridIcon } from "@/components/ui/layout-grid";
import { MessageSquareIcon } from "@/components/ui/message-square";
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
import { TutorSidebar } from "@/components/shell/TutorSidebar";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { PanelLeft } from "lucide-react";
import { useTwin } from "@/features/twin";
import { TutorHistoryResizeHandle, useTutorHistoryWidth } from "@/features/tutor";
import { GamificationSummary } from "@/features/gamification";
import { isDiagnosticDue, useDiagnosticStatus } from "@/features/diagnostic";
import { TourStepRunner } from "@/components/shell/StudentTour";
import {
  TOUR_STEPS,
  studentTourDismissKey,
} from "@/components/shell/student-tour";
import { cn } from "@/lib/utils";
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
  // Lessons / Practice / Flashcards collapsed into one entry (Checkpoint 3,
  // Step 3). They are three modes over one skill, not three destinations —
  // /course/lessons (Skills) is the skill picker that opens the hub, and the
  // hub's tabs launch each mode from there.
  { to: "/course/skills", label: "Skills", icon: GraduationCapIcon, anchorId: "nav-skills" },
  { to: "/course/tutor", label: "Tutor", icon: MessageSquareIcon, anchorId: "nav-tutor" },
  { to: "/course/twin", label: "Twin", icon: ActivityIcon, anchorId: "nav-twin" },
];

const SECTION_LABELS: Record<string, string> = {
  "/course": "Workspace",
  "/course/diagnostic": "Diagnostic",
  "/course/skills": "Skills",
  "/course/tutor": "Tutor",
  "/course/twin": "Twin",
};

// Routes whose FIRST path segment after /course/ is an id, not a section name.
// These are not in SECTION_LABELS (there is no static label to look up), so
// without this they fell through to the "/course" default and the breadcrumb
// read "Workspace" on a skill page. They resolve a section label from the
// route prefix plus a subsection from the data instead.
const DYNAMIC_SECTIONS: { prefix: string; section: string }[] = [
  { prefix: "/course/skill/", section: "Skills" },
];

const SESSION_ROUTES = [
  "/course/lessons",
  "/course/practice",
  "/course/flashcards",
  "/course/skill",
  "/course/diagnostic",
  "/course/tutor",
];

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
  const queryClient = useQueryClient();
  const [preparingTour, setPreparingTour] = useState(false);
  const tourSelectionRef = useRef(0);
  // Resolve a dynamic section (/course/skill/:id) before falling back to the
  // static map, so a skill page shows "Skills / <skill>" rather than the
  // Workspace default it used to inherit.
  const dynamic = DYNAMIC_SECTIONS.find((d) => pathname.startsWith(d.prefix));
  const section = dynamic
    ? dynamic.section
    : SECTION_LABELS[pathname] ?? SECTION_LABELS["/course"];
  // The skill id from the path, used only to label the crumb. useTwin is
  // already fetched by the hub itself, so this is a cache read, not a second
  // request, and it keeps the TopBar free of route-specific hooks.
  const skillId = dynamic ? pathname.slice(dynamic.prefix.length).split("/")[0] : undefined;
  const { data: twinForCrumb } = useTwin(courseId);
  const subsection = skillId
    ? twinForCrumb?.skills.find((s) => s.skillId === skillId)?.name
    : undefined;
  const isSessionRoute = SESSION_ROUTES.some((route) =>
    pathname === route || pathname.startsWith(`${route}/`)
  );
  // Tutor gets its own persistent left-rail extension (chat history — see
  // TutorSidebar), on every other route the icon rail is the whole story.
  const isTutorRoute = pathname.startsWith("/course/tutor");
  const [tutorHistoryOpen, setTutorHistoryOpen] = useState(false);
  const tutorHistory = useTutorHistoryWidth(isTutorRoute);
  const { data: diagnosticStatus } = useDiagnosticStatus(courseId);
  const diagnosticDue = isDiagnosticDue(diagnosticStatus);

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

  const startTour = async () => {
    if (preparingTour) return;
    setPreparingTour(true);
    const requestId = ++tourSelectionRef.current;
    try {
      // Read availability and existing sets before leaving the current topic.
      // Never select a random recommendation or a topic without material.
      const [bank, saved] = await Promise.all([fetchBankStatus(courseId), fetchPracticeSets(courseId)]);
      if (requestId !== tourSelectionRef.current) return;
      const currentSkillId = pathname.startsWith("/course/skill/") ? pathname.split("/")[3] : undefined;
      const readyLessons = queryClient.getQueriesData<Lesson>({ queryKey: ["lesson", courseId] })
        .map(([, lesson]) => lesson).filter((lesson) => lesson?.status === "ready" && lesson.steps.length);
      const sets = saved.sets.filter((set) => set.available !== false && set.status !== "unavailable");
      const candidates = bank.bankServing
        ? bank.skills.filter((skill) => skill.usable && skill.status !== "no_material" && skill.mcqReady >= 5)
        : (twinForCrumb?.skills ?? []).filter((skill) =>
            readyLessons.some((lesson) => lesson?.skillId === skill.skillId) ||
            (skill.moduleRef && sets.some((set) => set.skillId === skill.skillId && set.size >= 5)));
      const rank = (skillId: string) =>
        (skillId === currentSkillId ? 4 : 0) +
        (readyLessons.some((lesson) => lesson?.skillId === skillId) ? 8 : 0) +
        (sets.some((set) => set.skillId === skillId) ? 2 : 0);
      const chosen = candidates.sort((a, b) => rank(b.skillId) - rank(a.skillId))[0];
      if (!chosen) {
        toast.info("The tour needs a topic with at least five prepared questions. Open a ready topic and try again.");
        return;
      }
      const topicSets = sets.filter((set) => set.skillId === chosen.skillId);
      const set = topicSets.find((set) => (set.attemptedCount ?? 0) < set.size);
      useUI.getState().setTourContext({ skillId: chosen.skillId, setId: set?.setId, completedOnly: !set && topicSets.length > 0 });
      setConfirmOpen(false);
      useUI.getState().setTourStep(0);
      void navigate({ to: TOUR_STEPS[0].route });
    } catch {
      if (requestId === tourSelectionRef.current) toast.error("Could not check tour availability. Try again.");
    } finally {
      setPreparingTour(false);
    }
  };

  const closeTourConfirmation = () => {
    tourSelectionRef.current += 1;
    setConfirmOpen(false);
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
                      "relative flex h-9 w-9 items-center justify-center border-l-2 border-brand-orange bg-brand-orange/10 text-brand-orange",
                  }}
                  inactiveProps={{
                    className:
                      "relative flex h-9 w-9 items-center justify-center border-l-2 border-transparent text-muted-foreground/70 hover:bg-accent hover:text-foreground",
                  }}
                  // The ref switches each icon to controlled mode, which
                  // disables its native hover — so hover is forwarded to
                  // the handle here, on the BUTTON (the Link), not the
                  // icon: the rail icon draws when the nav button is
                  // hovered, and still draws on route activation.
                  onMouseEnter={() => iconHandles.current[i]?.startAnimation()}
                  onMouseLeave={() => iconHandles.current[i]?.stopAnimation()}
                  aria-label={
                    to === "/course/diagnostic" && diagnosticDue
                      ? `${label} (new baseline due)`
                      : label
                  }
                >
                  <Icon
                    size={18}
                    ref={(h) => {
                      iconHandles.current[i] = h ?? null;
                    }}
                  />
                  {to === "/course/diagnostic" && diagnosticDue ? (
                    <span
                      aria-hidden
                      className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-brand-orange"
                    />
                  ) : null}
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

      {isTutorRoute ? (
        <aside aria-label="Tutor chats" className="fixed inset-y-0 left-14 z-10 hidden border-r lg:block" style={{ width: tutorHistory.width }}>
          <TutorSidebar courseId={courseId} />
          <TutorHistoryResizeHandle width={tutorHistory.width} maxWidth={tutorHistory.maxWidth} onChange={tutorHistory.changeWidth} />
        </aside>
      ) : null}

      <div
        className={cn("flex h-dvh flex-col overflow-hidden", isTutorRoute && "pl-14 lg:pl-[var(--tutor-content-offset)]")}
        style={isTutorRoute ? { "--tutor-content-offset": `${56 + tutorHistory.width}px` } as CSSProperties : { paddingLeft: 56 }}
      >
        <div className="shrink-0">
          <TopBar
            courseId={courseId}
            section={section}
            subsection={subsection}
            right={
            <div className={cn("flex items-center gap-4", isTutorRoute && "gap-2 sm:gap-4")}>
              {isTutorRoute ? (
                <Sheet open={tutorHistoryOpen} onOpenChange={setTutorHistoryOpen}>
                  <SheetTrigger asChild><Button data-tour="tutor-history-mobile" variant="ghost" size="icon" className="lg:hidden" aria-label="Open chat history"><PanelLeft size={18} /></Button></SheetTrigger>
                  <SheetContent side="left" className="gap-0 p-0 motion-reduce:animate-none motion-reduce:transition-none">
                    <SheetTitle className="sr-only">Chat history</SheetTitle>
                    <SheetDescription className="sr-only">Choose a saved conversation or start a new chat.</SheetDescription>
                    <TutorSidebar courseId={courseId} onSelect={() => setTutorHistoryOpen(false)} />
                  </SheetContent>
                </Sheet>
              ) : null}
              {isTutorRoute ? <div className="hidden sm:block"><GamificationSummary courseId={courseId} /></div> : <GamificationSummary courseId={courseId} />}
              {/* One affordance, always: the quiet compass nav button. The
                  banner is the loud CTA when it is up; off-workspace there
                  is no banner, so the icon carries it — never a text
                  button that fights the icon language of the rail. */}
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
              <span className="font-mono text-xs text-muted-foreground">
                {initials(displayName) || section}
              </span>
            </div>
            }
          />
        </div>

        {bannerVisible ? (
          <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-brand-orange/20 bg-brand-orange/8 px-6 py-2.5">
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

        <main
          className={cn(
            isSessionRoute
              ? "flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-8 pb-24 lg:px-10 has-[>[data-study-surface]]:overflow-hidden has-[>[data-study-surface]]:p-0 has-[>[data-study-surface]]:lg:px-0"
              : "mx-auto min-h-0 w-full max-w-screen-2xl flex-1 overflow-y-auto px-6 py-8 pb-24 lg:px-10"
          )}
        >
          {children}
        </main>
      </div>

      {/* Pre-tour confirmation */}
      <Dialog open={confirmOpen} onOpenChange={(open) => open ? setConfirmOpen(true) : closeTourConfirmation()}>
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
              onClick={closeTourConfirmation}
              className="rounded-[3px] border border-primary/20 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-accent"
            >
              Maybe later
            </button>
            <button
              type="button"
              onClick={() => void startTour()}
              disabled={preparingTour}
              aria-busy={preparingTour}
              className="rounded-[3px] bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
            >
              {preparingTour ? <Spinner className="mr-1 inline-block" aria-hidden /> : null}
              {preparingTour ? <Spinner aria-hidden className="mr-2 inline-block size-3.5 align-middle" /> : null}
              {preparingTour ? "Checking topics…" : "Start tour"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
