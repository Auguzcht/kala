import type { ReactNode } from "react";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
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
import { cn } from "@/lib/utils";
import type { TwinSkill } from "@/features/twin";

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

const TABS: { id: SkillTab; label: string; icon: typeof GraduationCapIcon }[] = [
  { id: "lesson", label: "Lesson", icon: GraduationCapIcon },
  { id: "study", label: "Study", icon: LayersIcon },
  { id: "test", label: "Test", icon: ZapIcon },
];

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
  const { data: twin, isLoading } = useTwin(courseId);
  const skill: TwinSkill | undefined = twin?.skills.find((s) => s.skillId === skillId);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }
  if (!skill) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <EmptyState
          title="Skill not found"
          description="This skill isn't part of the course's approved map."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto h-full w-full max-w-3xl overflow-y-auto px-4 py-6">
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
        className="mt-4 flex items-center gap-1 border-b"
      >
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onSelectTab(id)}
              className={cn(
                "relative -mb-px flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "border-brand-orange text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon
                size={15}
                className={active ? "text-brand-orange" : "text-muted-foreground"}
                aria-hidden
              />
              {label}
            </button>
          );
        })}
      </div>

      <div className="mt-5">{children}</div>
    </div>
  );
}
