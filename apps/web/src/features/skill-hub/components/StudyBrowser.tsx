import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useFlashcardDeck } from "@/features/flashcards";
import type { FlashcardCard } from "@/features/flashcards";

// The Study tab's browse view — the materials list that sits in front of the
// sequential flip session, the same browse-then-commit shape the Test tab
// proved. Unlike Test, there is NO answer-key concern here: Study never grades,
// so each row shows BOTH sides of the card. That is the point of a materials
// list — you can see what you're about to review.
//
// Data comes from the existing deck endpoint (same assembly the session uses,
// just rendered as a list instead of one card at a time). The deck's top-up
// generation is what seeds a skill with no cards yet, so a first visit shows
// the freshly written cards rather than an empty screen with no way forward.
//
// The browse view is not study mode: it makes no scheduling writes and shows
// no flip UI. "Study deck" is what enters the session, which then owns the
// viewport as its own takeover.

// A generous cap so the list shows the whole tracked deck for one skill rather
// than the session's session-sized window of 10.
const BROWSE_LIMIT = 50;

export function StudyBrowser({
  courseId,
  skillId,
  onStart,
}: {
  courseId: string;
  skillId: string;
  /** Enter the sequential flip session. */
  onStart: () => void;
}) {
  const { data, isLoading, isError, refetch } = useFlashcardDeck(
    courseId,
    BROWSE_LIMIT,
    skillId,
  );

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }
  if (isError) {
    return (
      <EmptyState
        title="We could not load your cards"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  const cards = data?.cards ?? [];
  const stats = data?.stats;

  // Zero cards is a real state, not a loading artifact: either the skill has
  // nothing tracked yet (and the deck's top-up could not write any), or the
  // student has genuinely nothing left to review. Either way the list is empty
  // and the copy below says which, rather than landing on a dead end.
  if (cards.length === 0) {
    const allCaughtUp = (stats?.tracked ?? 0) > 0;
    return (
      <EmptyState
        title={allCaughtUp ? "All caught up" : "No cards yet"}
        description={
          allCaughtUp
            ? "Nothing is due for review on this skill right now. Missed cards resurface sooner — check back later, or take a test to keep your mastery moving."
            : "Kala couldn't write cards for this skill yet. Try again in a moment."
        }
        action={
          <Button variant="outline" onClick={() => refetch()}>
            Refresh
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* The one action this view exists to lead to. */}
      <div className="flex flex-wrap items-center justify-between gap-3 border bg-card px-5 py-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            {cards.length} {cards.length === 1 ? "card" : "cards"}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Recall each answer, then mark it yourself — Kala brings back what you miss.
          </p>
          {/* States the design decision out loud. Cards here are a
              spaced-repetition queue, seeded automatically, NOT a set you
              generate on demand — so the missing "generate more" button reads
              as intended rather than as an oversight. Generating cards would
              also raise a question the schedule can't answer: what due date
              does a brand-new card get, and should it jump ahead of cards that
              are actually due? */}
          <p className="mt-1 text-[11px] text-muted-foreground/80">
            Cards are added automatically for this skill as you study — this isn't a set you
            generate.
          </p>
        </div>
        <Button variant="orange" onClick={onStart} className="shrink-0">
          Study deck <ArrowRightIcon size={16} />
        </Button>
      </div>

      {/* Both sides shown: Study never grades, so there is nothing to hide. */}
      <ol className="divide-y divide-border border bg-card">
        {cards.map((card: FlashcardCard) => (
          <li key={card.itemId} className="flex flex-col gap-1 px-5 py-3.5">
            <div className="flex items-start justify-between gap-3">
              <p className="min-w-0 text-sm font-medium text-foreground">{card.prompt}</p>
              <StateBadge state={card.state} box={card.box} />
            </div>
            <div className="flex items-start gap-2">
              <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-brand-slate">
                Answer
              </span>
              <p className="min-w-0 text-sm text-muted-foreground">
                {card.back.label ?? "—"}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Small status pill: due vs new, plus the Leitner box. Mirrors the session
 * card's StateBadge language (orange = due, muted = new) so the list and the
 * session read as the same object. */
function StateBadge({ state, box }: { state: "due" | "new"; box: number }) {
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      <span
        className={cn(
          "rounded-full px-2 py-0.5 text-[10.5px] font-semibold",
          state === "due"
            ? "bg-brand-orange/15 text-foreground"
            : "bg-muted text-muted-foreground"
        )}
      >
        {state === "due" ? "Due" : "New"}
      </span>
      <span className="font-mono text-[10.5px] text-muted-foreground">box {box}</span>
    </span>
  );
}
