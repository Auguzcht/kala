import { useNavigate } from "@tanstack/react-router";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
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
// browsing, but every mode is keyed by skillId (lessons are per-skill, a quiz
// set is per-skill, the SRS deck is per-skill), so the hub has to be a skill.

export type SkillTab = "lesson" | "study" | "test";

const TABS: { id: SkillTab; label: string; icon: typeof GraduationCapIcon; blurb: string }[] = [
  { id: "lesson", label: "Lesson", icon: GraduationCapIcon, blurb: "Step-by-step walkthrough with checks." },
  { id: "study", label: "Study", icon: LayersIcon, blurb: "Flip cards. Self-paced, spaced repetition." },
  { id: "test", label: "Test", icon: ZapIcon, blurb: "Graded quiz that moves your mastery." },
];

export function SkillHub({
  courseId,
  skillId,
  tab,
  setId,
  start,
  onSelectSet,
  onStart,
  onExitSession,
}: {
  courseId: string;
  skillId: string;
  /** Active mode, or undefined while browsing the hub landing. Owned by the
   * route's search param so the hub is linkable and the "Next up" card can
   * deep-link straight to Test. */
  tab?: SkillTab;
  /** The set open in the Test tab's detail view (retake, bridge handoff, or
   * a freshly generated set). Empty string = back to the set list. */
  setId?: string;
  /** Test tab only: true once the student has committed to a graded run on
   * the open set, which is when PracticePanel takes over. Keeps "browse the
   * set" and "take the test" as two distinct steps. */
  start?: boolean;
  onSelectSet: (setId: string) => void;
  onStart: () => void;
  /** Leave the running session back to the hub landing (clears the tab in
   * the URL so a refresh doesn't re-enter it). */
  onExitSession: () => void;
}) {
  if (tab === "lesson") {
    return <LessonChat courseId={courseId} skillId={skillId} onExit={onExitSession} />;
  }
  if (tab === "study") {
    return <FlashcardDeck courseId={courseId} skillId={skillId} onExit={onExitSession} />;
  }
  if (tab === "test") {
    // Started -> the graded run. setId present = run that saved set; absent
    // = generate a fresh one (PracticePanel handles both, and the express
    // lane from "Next up" arrives here with no setId). Otherwise the browser:
    // a list of saved sets, or one set's detail.
    if (start) {
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
      <div className="mx-auto h-full w-full max-w-3xl overflow-y-auto px-4 py-8">
        <h1 className="font-display text-xl font-semibold text-foreground">Test</h1>
        <div className="mt-4">
          <TestBrowser
            courseId={courseId}
            skillId={skillId}
            setId={setId || null}
            onSelectSet={onSelectSet}
            onStart={onStart}
          />
        </div>
      </div>
    );
  }
  return <SkillHubLanding courseId={courseId} skillId={skillId} />;
}

// The hub's chrome: which skill, its mastery, and the mode launch cards.
// Rendered only when no mode is active — a mode owns the viewport through its
// own StudySurface/SessionBar takeover.
function SkillHubLanding({ courseId, skillId }: { courseId: string; skillId: string }) {
  const { data: twin, isLoading } = useTwin(courseId);
  const navigate = useNavigate();
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

  const go = (tab: SkillTab) =>
    navigate({ to: "/course/skill/$skillId", params: { skillId }, search: { tab } });

  return (
    <div className="mx-auto h-full w-full max-w-3xl overflow-y-auto px-4 py-8">
      {/* Skill header — the detail view TopicLanding's card promised, same
          data (name, Bloom level, mastery band), just not in a grid. */}
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

      {/* Mode launch cards. Each opens the existing session takeover. */}
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {TABS.map(({ id, label, icon: Icon, blurb }) => (
          <button
            key={id}
            type="button"
            onClick={() => go(id)}
            className={cn(
              "group border bg-card p-4 text-left transition-colors hover:bg-accent/60",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
          >
            <div className="mb-3 grid size-8 place-items-center rounded-[4px] bg-brand-slate">
              <Icon size={16} className="text-background" />
            </div>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground group-hover:underline">
              {label}
              <ArrowRightIcon size={14} />
            </div>
            <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{blurb}</div>
          </button>
        ))}
      </div>

    </div>
  );
}
