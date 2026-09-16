import type { ComponentType, ReactNode, Ref } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useNavigate } from "@tanstack/react-router";
import { BookOpenIcon } from "@/components/ui/book-open";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { LayersIcon } from "@/components/ui/layers";
import { ZapIcon } from "@/components/ui/zap";
import { MasteryBand } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useTwin } from "@/features/twin";
import { LessonChat } from "@/features/lessons";
import { FlashcardDeck } from "@/features/flashcards";
import { PracticePanel } from "@/features/practice";
import { StudyBrowser } from "@/features/skill-hub/components/StudyBrowser";
import { TestBrowser } from "@/features/skill-hub/components/TestBrowser";
import { useIconHover } from "@/hooks/use-icon-hover";
import { cn } from "@/lib/utils";
import type { TwinSkill } from "@/features/twin";

/** Animated icon shape shared by the tab strip (ref-driven imperative
 * startAnimation/stopAnimation, same as the rail's). */
type AnimatedIconHandle = { startAnimation: () => void; stopAnimation: () => void };
type AnimatedIcon = ComponentType<{
  size?: number;
  className?: string;
  ref?: Ref<AnimatedIconHandle>;
}>;

// The skill hub: ONE skill's page, with the three study modes as tabs over it.
// This is the "deck materials" move from docs/ai-overhaul-v2/05 (Option 2) —
// Gizmo's deck → modes, mapped onto Kala's real spine (course → module →
// skill). The rail and the Workspace grid both used to expose Lesson /
// Practice / Flashcards as three separate top-level destinations even though
// they are three ways to engage the SAME skill; that is what made them read as
// unrelated features. Here the skill is the hub and the modes launch from it.
//
// The modes are not rebuilt: LessonChat, FlashcardDeck, and PracticePanel are
// the exact session surfaces Phases 1–3 shipped, including the study→test
// bridge. This file only chooses which one is showing and provides the chrome
// to switch between them.
//
// Grain: a skill (skillId), not a module. TopicLanding groups by moduleRef for
// browsing, but every mode is keyed by skillId (lessons are per-skill, quiz
// sets are per-skill, the SRS deck is per-skill), so the hub has to be a skill.
//
// Structure: header + tab strip are the hub frame, and the pane below swaps
// with the tab. Study and Test have a BROWSE pane (which cards, which set /
// generate one) that lives under that frame; starting a session replaces the
// whole hub with the mode's own StudySurface takeover, which owns the viewport
// and therefore has no header or tabs. Lesson has no browse step by design —
// there is one guided walkthrough per skill, not several to choose among — so
// selecting Lesson goes straight into the takeover, collapsing "select the
// tab" and "enter the session" into the same click. The asymmetry is
// deliberate: the tab bar appears where browsing means something.

export type SkillTab = "lesson" | "study" | "test";

const TABS: { id: SkillTab; label: string; icon: AnimatedIcon }[] = [
  // BookOpen, not GraduationCap: the rail already uses graduation-cap for
  // Skills, and reusing it here made the Lesson tab read as a duplicate of its
  // own parent instead of a distinct mode.
  { id: "lesson", label: "Lesson", icon: BookOpenIcon },
  { id: "study", label: "Study", icon: LayersIcon },
  { id: "test", label: "Test", icon: ZapIcon },
];

/** A tab whose icon animates on hover of the WHOLE BUTTON, not the icon's own
 * few pixels — the same controlled-mode pattern the rail uses. Each tab needs
 * its own ref, so this has to be a component rather than an inline map. */
function HubTab({
  id,
  label,
  icon: Icon,
  active,
  onSelect,
}: {
  id: SkillTab;
  label: string;
  icon: AnimatedIcon;
  active: boolean;
  onSelect: (tab: SkillTab) => void;
}) {
  const icon = useIconHover<AnimatedIconHandle>();
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => onSelect(id)}
      onMouseEnter={icon.play}
      onMouseLeave={icon.stop}
      onFocus={icon.play}
      onBlur={icon.stop}
      className={cn(
        // A segmented control, not a hairline underline. The old active state
        // was a 2px orange bottom border plus near-identical text, which was
        // too subtle to read as "you are here" — especially next to the
        // bordered header above it. Filled background + border + orange icon
        // makes the selection unambiguous at a glance.
        "relative -mb-px flex items-center gap-1.5 rounded-t-[3px] border border-b-0 px-3.5 py-2.5 text-sm font-semibold transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "border-border bg-card text-foreground"
          : "border-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )}
    >
      {/* The active tab's marker: an orange rule on the tab's own top edge,
          matching the orange used for the current section in the rail. */}
      {active ? (
        <span
          aria-hidden
          className="absolute inset-x-0 -top-px h-0.5 rounded-full bg-brand-orange"
        />
      ) : null}
      <Icon
        ref={icon.ref}
        size={15}
        aria-hidden
        className={active ? "text-brand-orange" : undefined}
      />
      {label}
    </button>
  );
}

export function SkillHub({
  courseId,
  skillId,
  tab,
  setId,
  start,
  onSelectTab,
  onSelectSet,
  onStart,
  onExitSession,
}: {
  courseId: string;
  skillId: string;
  /** Active mode. Owned by the route's search param so the hub is linkable and
   * the "Next up" card can deep-link straight to Test. */
  tab?: SkillTab;
  /** The set open in the Test tab's detail view (retake, bridge handoff, or
   * a freshly generated set). Empty string = back to the set list. */
  setId?: string;
  /** True once a session is running (Study's flip deck, Test's graded run).
   * Replaces the hub frame with the mode's own takeover. */
  start?: boolean;
  onSelectTab: (tab: SkillTab) => void;
  onSelectSet: (setId: string) => void;
  onStart: () => void;
  /** Leave a running session back to the hub pane (clears `start` in the URL
   * so a refresh doesn't re-enter it). */
  onExitSession: () => void;
}) {
  // Lesson has nothing to browse: entering the tab IS entering the session.
  // Its exit returns to the hub with the Study pane active (see the route),
  // because a bare `tab=lesson` would immediately re-enter the session.
  if (tab === "lesson") {
    return <LessonChat courseId={courseId} skillId={skillId} onExit={onExitSession} />;
  }

  // A running session owns the viewport (no header, no tabs) — the same
  // takeover contract every mode already has.
  if (tab === "study" && start) {
    return <FlashcardDeck courseId={courseId} skillId={skillId} onExit={onExitSession} />;
  }
  if (tab === "test" && start) {
    return (
      <PracticePanel
        courseId={courseId}
        skillId={skillId}
        setId={setId || null}
        onExit={onExitSession}
      />
    );
  }

  return (
    <SkillHubFrame
      courseId={courseId}
      skillId={skillId}
      // No tab in the URL (a bare hub visit, or Lesson's exit) lands on Study:
      // the first tab that has a browse pane to actually show.
      activeTab={tab ?? "study"}
      onSelectTab={onSelectTab}
    >
      {tab === "test" ? (
        <TestBrowser
          courseId={courseId}
          skillId={skillId}
          setId={setId || null}
          onSelectSet={onSelectSet}
          onStart={onStart}
        />
      ) : (
        <StudyBrowser courseId={courseId} skillId={skillId} onStart={onStart} />
      )}
    </SkillHubFrame>
  );
}

/** The hub frame: skill header, tab strip, and whichever pane is active.
 * Shown only while browsing (see the module comment on why Lesson skips it). */
function SkillHubFrame({
  courseId,
  skillId,
  activeTab,
  onSelectTab,
  children,
}: {
  courseId: string;
  skillId: string;
  activeTab?: SkillTab;
  onSelectTab: (tab: SkillTab) => void;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const { data: twin, isLoading } = useTwin(courseId);
  const reduceMotion = useReducedMotion();
  const skill: TwinSkill | undefined = twin?.skills.find((s) => s.skillId === skillId);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-[1040px] px-4 py-8">
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }
  if (!skill) {
    return (
      <div className="mx-auto max-w-[1040px] px-4 py-8">
        <EmptyState
          title="Skill not found"
          description="This skill isn't part of the course's approved map."
        />
      </div>
    );
  }

  return (
    // NOT a scroll container. CourseShell's <main> already owns the scroll for
    // non-takeover routes (it is `overflow-y-auto` with its own bottom
    // padding), so making this pane `h-full overflow-y-auto` too created TWO
    // nested scroll owners: `h-full` resolves against a scrolling parent's
    // unbounded content height, so the inner box never sized correctly and its
    // own horizontal overflow surfaced as a stray scrollbar. This pane is a
    // plain block in main's scroll; pb-24 here clears the fixed dock so the
    // last row of cards is not hidden behind it.
    <div className="mx-auto w-full max-w-[1040px] px-4 pb-24 pt-2">
      {/* Back to the skill picker — the hub is reached FROM Skills, so there
          has to be a way back that is not the browser button. Sits above the
          header, quiet, matching the session bar's back affordance. */}
      <button
        type="button"
        onClick={() => navigate({ to: "/course/skills" })}
        className="mb-3 inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ChevronLeftIcon size={14} /> All skills
      </button>
      {/* Skill header — unchanged from the tile version: title, mastery band,
          and the bloom/module/attempts line. The one part that already read
          right, so the tab change is confined to what sits under it. */}
      <div className="border bg-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-xl font-semibold text-foreground">{skill.name}</h1>
          <MasteryBand band={skill.band} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {skill.bloomLevel ? (
            <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-semibold capitalize">
              {skill.bloomLevel}
            </span>
          ) : null}
          {skill.moduleRef ? <span className="capitalize">{skill.moduleRef}</span> : null}
          <span className="font-mono">
            {skill.attempts} {skill.attempts === 1 ? "attempt" : "attempts"}
          </span>
        </div>
      </div>

      {/* Tab strip. A content switch, not three navigation targets, so it reads
          as tabs (underline on the active item) rather than a second row of
          cards competing with the header above it. */}
      <div
        role="tablist"
        aria-label="Study modes"
        className="mt-4 flex items-end gap-1 border-b"
      >
        {TABS.map(({ id, label, icon }) => (
          <HubTab
            key={id}
            id={id}
            label={label}
            icon={icon}
            active={activeTab === id}
            onSelect={onSelectTab}
          />
        ))}
      </div>

      {/* Pane transition: a short fade+rise on tab change, so switching modes
          reads as a content swap rather than a hard cut. Keyed on activeTab so
          it replays per switch; reduced-motion drops to no animation. */}
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={activeTab ?? "study"}
          initial={reduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}
          className="mt-5"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
