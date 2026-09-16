import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { PlusIcon } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useGenerateSet,
  usePracticeSetById,
  usePracticeSets,
} from "@/features/practice";
import type { PracticeSetAttempt, PracticeSetSummary } from "@/features/practice";

// The Test tab's browser: saved sets for one skill, browse before you commit.
// Picking a set (or generating a new one) opens its DETAIL view — prompts only
// — and only the detail view's "Start test" begins the graded run. That extra
// beat is the point: a graded test moves mastery, so it should be an explicit
// choice, not the accidental consequence of tapping a card in a list.
//
// The answer key is never here. The detail view renders prompts and nothing
// else; grading stays server-side on submit, exactly as before. This is a
// graded test, not a flashcard browse (see routers/practice.py's get_set).
//
// "Next up" on the Workspace deliberately does NOT route through this browser
// — that card already tells the student what to do, so it deep-links straight
// to ?tab=test&start=1. This browser is for entering Test deliberately.

const SET_SIZE = 5;

// The card header bar's color, cycled through the existing brand tokens. Keyed
// by a stable hash of the set id rather than list position: the spec asked for
// cycling-by-index so a set keeps its color across reloads, and hashing gets
// exactly that while ALSO giving the SAME color to the same set in the detail
// view (which has no list index to read). No new tokens introduced.
const BAR_COLORS = ["bg-brand-orange", "bg-brand-gold", "bg-brand-green", "bg-brand-slate"] as const;

function barColor(setId: string): string {
  let h = 0;
  for (let i = 0; i < setId.length; i++) h = (h * 31 + setId.charCodeAt(i)) >>> 0;
  return BAR_COLORS[h % BAR_COLORS.length];
}

export function TestBrowser({
  courseId,
  skillId,
  setId,
  onSelectSet,
  onStart,
}: {
  courseId: string;
  skillId: string;
  /** When set, show that set's detail view instead of the list. */
  setId: string | null;
  /** Open a set's detail view (from the list, or after generating). */
  onSelectSet: (setId: string) => void;
  /** Begin the graded run on the currently open set. */
  onStart: () => void;
}) {
  if (setId) {
    return (
      <SetDetail
        courseId={courseId}
        setId={setId}
        onStart={onStart}
        onBack={() => onSelectSet("")}
      />
    );
  }
  return <SetList courseId={courseId} skillId={skillId} onSelectSet={onSelectSet} />;
}

/** The attempt state as a small scannable pill: muted when untouched, green
 * when the student has answers on record. Never red — a score here is
 * informational, not a verdict (the mastery palette reserves red for the
 * instructor at-risk axis). */
function AttemptPill({ attempt }: { attempt: PracticeSetAttempt }) {
  if (attempt.attemptedCount === null) {
    return (
      <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10.5px] font-semibold text-muted-foreground">
        Not attempted
      </span>
    );
  }
  const correct = attempt.correctCount ?? 0;
  return (
    <span className="inline-flex items-center rounded-full bg-brand-green/15 px-2 py-0.5 text-[10.5px] font-semibold text-foreground">
      {correct}/{attempt.attemptedCount} correct
    </span>
  );
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** The 8px full-width bar at the top of every card. Its color is the set's
 * identity, carried into the detail view so opening a card feels like opening
 * the same object rather than navigating somewhere unrelated. */
function CardBar({ setId }: { setId: string }) {
  return <div className={cn("h-2 w-full rounded-t-[3px]", barColor(setId))} aria-hidden />;
}

function SetList({
  courseId,
  skillId,
  onSelectSet,
}: {
  courseId: string;
  skillId: string;
  onSelectSet: (setId: string) => void;
}) {
  const { data, isLoading, isError, refetch } = usePracticeSets(courseId, skillId);
  const generate = useGenerateSet(courseId);
  const sets = data?.sets ?? [];

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (isError) {
    return (
      <EmptyState
        title="We could not load your tests"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  const onGenerate = () => {
    generate.mutate(
      { skillId, size: SET_SIZE },
      { onSuccess: (set) => { if (set.setId) onSelectSet(set.setId); } }
    );
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        A graded check on this skill — it moves your mastery. Pick a set to see
        what's in it before you start.
      </p>

      {sets.length === 0 ? (
        <div className="border border-dashed bg-card px-5 py-4">
          <p className="text-sm font-semibold text-foreground">No saved tests yet</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Generate one below, or study these cards and hit "Test me on these" —
            saved sets land here to retake.
          </p>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        {/* Real sets. */}
        {sets.map((set: PracticeSetSummary) => (
          <button
            key={set.setId}
            type="button"
            onClick={() => onSelectSet(set.setId)}
            className={cn(
              "group flex flex-col overflow-hidden border bg-card text-left",
              "transition-[border-color,box-shadow] hover:border-foreground/30 hover:shadow-md",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
          >
            <CardBar setId={set.setId} />
            <div className="flex flex-1 flex-col gap-3 p-4">
              <div className="min-w-0">
                <p className="font-display text-base font-semibold text-foreground group-hover:underline">
                  {set.size} {set.size === 1 ? "question" : "questions"}
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                  {fmtDate(set.createdAt)}
                </p>
              </div>
              <div className="mt-auto flex flex-wrap items-center gap-2">
                <AttemptPill attempt={set} />
                {set.lastAttemptedAt ? (
                  <span className="text-[11px] text-muted-foreground">
                    last {fmtDate(set.lastAttemptedAt)}
                  </span>
                ) : null}
              </div>
            </div>
          </button>
        ))}

        {/* Generate — SAME footprint as a real set card so it sits in the grid
            as a peer, but a dashed border and centered icon keep it visually
            distinct: it is an action, not a saved set you might have taken. */}
        <button
          type="button"
          onClick={onGenerate}
          disabled={generate.isPending}
          className={cn(
            "group flex flex-col items-center justify-center gap-2 rounded-[3px] border border-dashed border-muted-foreground/40 bg-card/50 p-4 text-center",
            "transition-[border-color,background-color] hover:border-foreground/40 hover:bg-accent/40",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            generate.isPending && "opacity-60"
          )}
        >
          <div className="grid size-9 place-items-center rounded-full border border-dashed border-muted-foreground/40">
            <PlusIcon size={18} className="text-muted-foreground" />
          </div>
          <p className="text-sm font-semibold text-foreground">
            {generate.isPending ? "Writing your questions…" : "Generate new set"}
          </p>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Fresh questions, {SET_SIZE} at a time.
          </p>
          {generate.isError ? (
            <p className="text-xs text-destructive">
              Kala could not write questions just now. Try again.
            </p>
          ) : null}
        </button>
      </div>
    </div>
  );
}

function SetDetail({
  courseId,
  setId,
  onStart,
  onBack,
}: {
  courseId: string;
  setId: string;
  onStart: () => void;
  onBack: () => void;
}) {
  const { data, isLoading, isError, refetch } = usePracticeSetById(courseId, setId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <EmptyState
        title="We could not load this set"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  const attempted = data.attemptedCount !== null;
  const attempt: PracticeSetAttempt = {
    attemptedCount: data.attemptedCount,
    correctCount: data.correctCount,
    lastAttemptedAt: data.lastAttemptedAt,
  };

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="text-xs font-semibold text-muted-foreground hover:text-foreground"
      >
        ← All tests
      </button>

      {/* Header repeats the card's color bar and size/date, so grid -> detail
          reads as opening the same object. */}
      <div className="overflow-hidden border bg-card">
        <CardBar setId={data.setId} />
        <div className="flex flex-wrap items-center justify-between gap-3 p-5">
          <div className="min-w-0">
            <p className="font-display text-lg font-semibold text-foreground">
              {data.items.length} {data.items.length === 1 ? "question" : "questions"}
            </p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <AttemptPill attempt={attempt} />
              {data.lastAttemptedAt ? (
                <span className="text-[11px] text-muted-foreground">
                  last {fmtDate(data.lastAttemptedAt)}
                </span>
              ) : null}
            </div>
          </div>
          {/* The single action this whole view exists to lead to — solid and
              high-contrast, not another card in the stack. */}
          <Button variant="orange" size="lg" onClick={onStart} className="shrink-0">
            {attempted ? "Retake test" : "Start test"} <ArrowRightIcon size={16} />
          </Button>
        </div>
      </div>

      {/* Prompts only — no choices or answers, by design. Grading is
          server-side on submit; this is a graded test, not a flashcard browse. */}
      <div className="divide-y divide-border border bg-card">
        {data.items.map((item, i) => (
          <div key={item.id} className="flex gap-3 px-5 py-3">
            <span className="font-mono text-xs text-muted-foreground">{i + 1}</span>
            <p className="min-w-0 text-sm text-foreground">{item.prompt}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
