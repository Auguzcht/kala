import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { PlusIcon } from "lucide-react";
import { ZapIcon } from "@/components/ui/zap";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useGenerateSet,
  usePracticeSetById,
  usePracticeSets,
} from "@/features/practice";
import type { PracticeSetSummary } from "@/features/practice";

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
      <SetDetail courseId={courseId} setId={setId} onStart={onStart} onBack={() => onSelectSet("")} />
    );
  }
  return (
    <SetList courseId={courseId} skillId={skillId} onSelectSet={onSelectSet} />
  );
}

function attemptBadge(set: PracticeSetSummary) {
  if (set.attemptedCount === null) {
    return (
      <span className="rounded-sm border border-border bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold text-muted-foreground">
        Not attempted
      </span>
    );
  }
  const correct = set.correctCount ?? 0;
  // A score badge is informational, never a grade — no red for "failed".
  // Gold when everything right, slate otherwise, matching the mastery palette.
  const allRight = correct === set.attemptedCount && set.attemptedCount > 0;
  return (
    <span
      className={cn(
        "rounded-sm px-1.5 py-0.5 text-[10.5px] font-semibold",
        allRight ? "bg-brand-gold/20 text-foreground" : "bg-brand-slate/10 text-foreground"
      )}
    >
      {correct}/{set.attemptedCount} correct
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
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
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

      <div className="grid gap-3 sm:grid-cols-2">
        {/* Real sets first. */}
        {sets.map((set) => (
          <button
            key={set.setId}
            type="button"
            onClick={() => onSelectSet(set.setId)}
            className="group border bg-card p-4 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground group-hover:underline">
                  {set.size} {set.size === 1 ? "question" : "questions"}
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                  {fmtDate(set.createdAt)}
                </p>
              </div>
              <div className="grid size-8 shrink-0 place-items-center rounded-[4px] bg-brand-slate">
                <ZapIcon size={16} className="text-background" />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {attemptBadge(set)}
              {set.lastAttemptedAt ? (
                <span className="text-[11px] text-muted-foreground">
                  last {fmtDate(set.lastAttemptedAt)}
                </span>
              ) : null}
            </div>
          </button>
        ))}

        {/* Generate — visually distinct (dashed, muted) so it never reads as
            an existing set you might have already attempted. */}
        <button
          type="button"
          onClick={onGenerate}
          disabled={generate.isPending}
          className={cn(
            "group flex flex-col justify-center border border-dashed bg-card/50 p-4 text-left",
            "transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            generate.isPending && "opacity-60"
          )}
        >
          <div className="mb-2 grid size-8 place-items-center rounded-[4px] border border-dashed border-muted-foreground/40">
            <PlusIcon size={16} className="text-muted-foreground" />
          </div>
          <p className="text-sm font-semibold text-foreground">
            {generate.isPending ? "Writing your questions…" : "Generate new set"}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Fresh questions on this skill, {SET_SIZE} at a time.
          </p>
          {generate.isError ? (
            <p className="mt-2 text-xs text-destructive">
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border bg-card px-5 py-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            {data.items.length} {data.items.length === 1 ? "question" : "questions"}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {attemptBadge({
              setId: data.setId, skillId: data.skillId, kind: data.kind,
              size: data.items.length, createdAt: "",
              attemptedCount: data.attemptedCount,
              correctCount: data.correctCount,
              lastAttemptedAt: data.lastAttemptedAt,
            })}
            {data.lastAttemptedAt ? (
              <span className="text-[11px] text-muted-foreground">
                last {fmtDate(data.lastAttemptedAt)}
              </span>
            ) : null}
          </div>
        </div>
        <Button variant="orange" onClick={onStart} className="shrink-0">
          {attempted ? "Retake test" : "Start test"} <ArrowRightIcon size={16} />
        </Button>
      </div>

      {/* Prompts only — no answer key, by design. Grading is server-side on
          submit; this is a graded test, not a flashcard browse. */}
      <div className="divide-y divide-border border bg-card">
        {data.items.map((item, i) => (
          <div key={item.id} className="flex gap-3 px-5 py-3">
            <span className="font-mono text-xs text-muted-foreground">{i + 1}</span>
            <p className="min-w-0 text-sm text-foreground">{item.prompt}</p>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onBack}
        className="text-xs font-semibold text-muted-foreground hover:text-foreground"
      >
        ← All tests
      </button>
    </div>
  );
}
