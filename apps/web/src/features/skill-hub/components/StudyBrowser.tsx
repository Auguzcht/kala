import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { Clock3Icon } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useFlashcardMembership } from "@/features/flashcards/hooks/use-flashcards";
import type { FlashcardMembershipCard } from "@/features/flashcards/schema/flashcards.schema";
import { useBankStatus } from "@/features/bank";
import { cardStatePresentation } from "@/features/flashcards/lib/card-state";

// The Study tab's browse view — the materials list that sits in front of the
// sequential flip session, the same browse-then-commit shape the Test tab
// proved. Unlike Test, there is NO answer-key concern here: Study never grades,
// so each row shows BOTH sides of the card. That is the point of a materials
// list — you can see what you're about to review.
//
// Data comes from the membership endpoint, independent of the session queue.
// That keeps Known cards visible while session selection stays due-first.
//
// The browse view is not study mode: it makes no scheduling writes and shows
// no flip UI. "Study deck" is what enters the session, which then owns the
// viewport as its own takeover.

export function StudyBrowser({
  courseId,
  skillId,
  onStart,
}: {
  courseId: string;
  skillId: string;
  /** Enter the sequential flip session. */
  onStart: (mode: "review" | "all") => void;
}) {
  const { data, isLoading, isError, refetch } = useFlashcardMembership(courseId, skillId);
  const bank = useBankStatus(courseId);
  const bankSkill = bank.data?.skills.find((entry) => entry.skillId === skillId);
  const isNoMaterial = bank.data?.bankServing === true && bankSkill?.status === "no_material";
  const isPreparing = bank.data?.bankServing === true &&
    !isNoMaterial && !bankSkill?.usable;
  const reduceMotion = useReducedMotion();

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

  // An empty response can mean a bank build is still below its usable threshold,
  // the skill has no course material, or the student's SRS queue is empty.
  if (cards.length === 0) {
    if (bank.isLoading) {
      return <LoadingPanel label="Checking card availability…" lines={3} />;
    }
    if (isNoMaterial) {
      return (
        <EmptyState
          title="No course material yet"
          description="This skill doesn&apos;t have course material yet."
        />
      );
    }
    if (isPreparing) {
      return (
        <LoadingPanel
          label={`Preparing questions (${bankSkill?.mcqReady ?? 0} of ${bankSkill?.mcqTarget ?? 0})`}
          lines={3}
        />
      );
    }
    if (bank.isError) {
      return (
        <EmptyState
          title="We could not check card availability"
          description="Reload this page to try again."
          action={<Button variant="outline" onClick={() => refetch()}>Reload deck</Button>}
        />
      );
    }
    const allCaughtUp = data?.isFallback === true && (data.fallbackTracked ?? 0) > 0;
    return (
      <EmptyState
        title={allCaughtUp ? "All caught up" : "No cards yet"}
        description={
          allCaughtUp
            ? "Nothing is due for review on this skill right now. Missed cards resurface sooner. Check back later or take a test to keep your mastery moving."
            : "No cards are available for this skill right now."
        }
        action={allCaughtUp ? <Button variant="outline" onClick={() => refetch()}>Reload deck</Button> : undefined}
      />
    );
  }

  const counts = data?.counts ?? { new: 0, learning: 0, slipping: 0, known: 0, dueToday: 0 };
  const memoryTotal = counts.new + counts.learning + counts.slipping + counts.known;
  const summaryStates = ["new", "learning", "slipping", "known"] as const;

  return (
    <div className="space-y-4">
      {/* Review the due queue or open the full skill deck. */}
      <div className="grid gap-4 border bg-card px-5 py-4 sm:grid-cols-[1fr_auto] sm:items-center">
        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-between gap-4">
            <p className="font-display text-lg font-semibold text-foreground">{cards.length} cards</p>
            <div className="text-right sm:hidden">
              <p className="font-display text-xl font-semibold leading-none text-foreground">{counts.dueToday}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">due today</p>
            </div>
          </div>
          <div
            className="flex h-2 w-full overflow-hidden"
            role="img"
            aria-label={`Card memory: ${counts.new} new, ${counts.learning} learning, ${counts.slipping} slipping, ${counts.known} known`}
          >
            {summaryStates.map((state) => {
              const presentation = cardStatePresentation(state);
              const count = counts[state];
              return count > 0 ? (
                <span
                  key={state}
                  className={presentation.fillClassName}
                  style={{ width: `${memoryTotal ? (count / memoryTotal) * 100 : 0}%` }}
                />
              ) : null;
            })}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5" aria-label="Card memory summary">
            {summaryStates.map((state) => {
              const presentation = cardStatePresentation(state);
              return (
                <span key={state} className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className={cn("size-2 shrink-0", presentation.fillClassName)} aria-hidden />
                  {presentation.label} <span className="font-mono tabular-nums">{counts[state]}</span>
                </span>
              );
            })}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Recall each answer, then mark it yourself. Missed cards return sooner.
          </p>
        </div>
        <div className="hidden min-w-24 text-right sm:block">
          <p className="font-display text-2xl font-semibold leading-none text-foreground">{counts.dueToday}</p>
          <p className="mt-1 text-[11px] text-muted-foreground">due today</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button
            variant="orange"
            onClick={() => onStart("review")}
            disabled={data?.counts.dueToday === 0}
          >
            {data?.counts.dueToday === 0 ? "All caught up" : `Review due (${data?.counts.dueToday ?? 0})`}
            <ArrowRightIcon size={16} />
          </Button>
          <Button variant="outline" onClick={() => onStart("all")}>
            Study all
          </Button>
        </div>
      </div>

      {bank.data?.bankServing && bankSkill?.status === "building" && bankSkill.usable ? (
        <p className="border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
          More questions on the way.
        </p>
      ) : null}
      {bank.data?.bankServing &&
      ["waiting_content", "building", "error"].includes(bankSkill?.status ?? "waiting_content") &&
      !bankSkill?.usable ? (
        <p className="border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
          Preparing questions ({bankSkill?.mcqReady ?? 0} of {bankSkill?.mcqTarget ?? 0}).
        </p>
      ) : null}

      {/* Both sides shown: Study never grades, so there is nothing to hide. */}
      <ol aria-label="Study cards" className="divide-y divide-border border bg-card">
        {cards.map((card: FlashcardMembershipCard, i: number) => (
          <motion.li
            key={card.itemId}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.18), ease: "easeOut" }}
            className="flex flex-col gap-1 px-5 py-3.5"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="min-w-0 text-sm font-medium text-foreground">{card.prompt}</p>
              <StateBadge state={card.state} due={card.due} />
            </div>
            <div className="flex items-start gap-2 border-l-2 border-brand-green/40 pl-3">
              <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Answer
              </span>
              <p className="min-w-0 text-sm leading-relaxed text-muted-foreground">
                {card.back.label ?? "No answer label"}
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}

/** Card memory state is separate from the skill mastery band shown above. */
function StateBadge({ state, due }: { state: FlashcardMembershipCard["state"]; due: boolean }) {
  const presentation = state === "due" ? null : cardStatePresentation(state);
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      {presentation ? (
        <span className={cn("rounded-sm border px-2 py-0.5 text-[10.5px] font-semibold", presentation.className)}>
          {presentation.label}
        </span>
      ) : null}
      {due || state === "due" ? (
        <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold text-brand-orange">
          <Clock3Icon size={12} aria-hidden />
          Due
        </span>
      ) : null}
    </span>
  );
}
