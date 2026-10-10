import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { motion, useReducedMotion } from "motion/react";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useFlashcardMembership } from "@/features/flashcards/hooks/use-flashcards";
import type { FlashcardMembershipCard } from "@/features/flashcards/schema/flashcards.schema";
import { useBankStatus } from "@/features/bank";

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
  onStart: () => void;
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

  return (
    <div className="space-y-4">
      {/* The one action this view exists to lead to. */}
      <div className="flex flex-wrap items-center justify-between gap-3 border bg-card px-5 py-4">
        <div className="min-w-0 space-y-2">
          <p className="text-sm font-semibold text-foreground">
            {data?.isFallback ? `${cards.length} to review` : `${cards.length} ${cards.length === 1 ? "card" : "cards"}`}
          </p>
          {!data?.isFallback ? (
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Card memory summary">
              <span>{data?.counts.new ?? 0} new</span>
              <span>{data?.counts.learning ?? 0} learning</span>
              <span>{data?.counts.slipping ?? 0} slipping</span>
              <span>{data?.counts.known ?? 0} known</span>
              <span>{data?.counts.dueToday ?? 0} due today</span>
            </div>
          ) : null}
          <p className="mt-0.5 text-xs text-muted-foreground">
            Recall each answer, then mark it yourself. Missed cards return sooner.
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Cards are added to your review queue as you study.
          </p>
        </div>
        <Button variant="orange" onClick={onStart} className="shrink-0">
          Study deck <ArrowRightIcon size={16} />
        </Button>
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
      <ol className="divide-y divide-border border bg-card">
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
            <div className="flex items-start gap-2">
              <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-brand-slate">
                Answer
              </span>
              <p className="min-w-0 text-sm text-muted-foreground">
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
  const label = state === "due" ? "Due" : state[0].toUpperCase() + state.slice(1);
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      <span
        className={cn(
          "rounded-sm px-2 py-0.5 text-[10.5px] font-semibold",
          due
            ? "bg-brand-orange/15 text-foreground"
            : "bg-muted text-muted-foreground"
        )}
      >
        {label}
      </span>
      {due && state !== "due" ? (
        <span className="text-[10.5px] text-brand-orange">Due</span>
      ) : null}
    </span>
  );
}
