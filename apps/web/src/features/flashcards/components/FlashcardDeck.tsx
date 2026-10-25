import { useSession } from "@/lib/auth/AuthProvider";
import { readReviewProgress, writeReviewProgress } from "@/features/flashcards/lib/review-progress";
import { SessionState } from "@/components/study/SessionState";
import { forwardRef, useEffect, useId, useImperativeHandle, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { BrainIcon } from "@/components/ui/brain";
import { SparklesIcon } from "@/components/ui/sparkles";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock, type ComposeDockPrimary } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";
import { UserBlock } from "@/components/study/UserBlock";
import { CornerBrackets } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { CheckIcon } from "@/components/ui/check";
import { RotateCCWIcon } from "@/components/ui/rotate-ccw";
import { Clock3Icon } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { celebrateOnce } from "@/lib/celebrate";
import { cn } from "@/lib/utils";
import {
  useFlashcardDeck,
  useFlashcardMembership,
  useReviewFlashcard,
} from "@/features/flashcards/hooks/use-flashcards";
import { usePracticeSetResults } from "@/features/practice";
import { useBankStatus } from "@/features/bank";
import { useTwin } from "@/features/twin";
import { useTutorAsk } from "@/features/tutor";
import type { FlashcardCard, FlashcardDeck as FlashcardDeckData } from "@/features/flashcards/schema/flashcards.schema";
import { cardStatePresentation } from "@/features/flashcards/lib/card-state";

// Study mode: a flip card, not a quiz. Front shows the prompt, tapping flips
// to the back (answer label + explanation), and the student marks it "Got it"
// or "Still learning" themselves. That self-mark advances the spaced-repetition
// schedule so weak cards resurface sooner, but it does NOT feed the twin —
// self-report is not assessment (see routers/flashcards.py). Test sessions
// are started separately from the skill hub's Test tab.
//
// The contrast with PracticePanel is the whole point of the split: practice is
// a graded MCQ (server decides correctness, moves mastery), study is a flip
// (student decides, moves only the schedule). Same question underneath,
// two honest modes.
//
// One topic choice per session (see
// docs/features/study/README.md#learning-surface-boundaries), but NOT one required skill — `skillId` stays
// optional here on purpose. Practice and Lessons both resolve to exactly
// one skill either way (a specific pick, or the single weakest skill).
// Flashcards' natural default is different: "due for review" is a
// cross-skill deck, whatever's due across everything, not a single
// skill's queue. Forcing a skillId here would drop that mode entirely,
// not just simplify the UI — so the choice made on the landing page
// (routes/course/flashcards.tsx) is either "review what's due" (no
// skillId) or a specific skill from the grid (skillId set), and this
// component just runs whichever it's given for the whole session. What
// IS gone is the in-deck picker to switch mid-session — same rationale
// as PracticePanel, that's a route-level action now (the "Choose another
// topic" back button), not something this component offers.

type Phase = "front" | "back";
type FollowUpTurn = { question: string; answer: string };
type ReviewIconHandle = { startAnimation: () => void; stopAnimation: () => void };

const ReviewSpinnerIcon = forwardRef<ReviewIconHandle, { size?: number }>(function ReviewSpinnerIcon(
  { size = 16 },
  ref,
) {
  useImperativeHandle(ref, () => ({ startAnimation: () => undefined, stopAnimation: () => undefined }), []);
  return <Spinner aria-label="Saving review" style={{ width: size, height: size }} />;
});

function StateBadge({ state }: { state: FlashcardCard["state"] }) {
  const presentation = state === "due" ? null : cardStatePresentation(state);
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-[10.5px] font-semibold",
        presentation?.className ?? "border-brand-orange/40 bg-brand-orange/10 text-brand-orange"
      )}
    >
      {state === "due" ? <Clock3Icon size={12} aria-hidden /> : null}
      {presentation?.label ?? "Due"}
    </span>
  );
}

export function FlashcardDeck({
  courseId,
  skillId,
  mode = "review",
  practiceSetId,
  practiceAttemptId,
  missedItemIds,
  onReviewDone,
  onExit,
}: {
  courseId: string;
  skillId?: string;
  mode?: "review" | "all";
  /** When present, study only the questions missed in this saved test set. */
  practiceSetId?: string;
  practiceAttemptId?: string;
  /** Exact missed items from the recap attempt that opened this review. */
  missedItemIds?: string[];
  /** Return to the saved test recap after the missed items are reviewed. */
  onReviewDone?: (setId: string) => void;
  onExit: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const replySessionId = useId();
  const contentEpochRef = useRef(0);
  const userId = useSession()?.userId;
  const progressKey = practiceSetId && userId
    ? `kala:missed-review:v1:${JSON.stringify([userId, courseId, skillId, practiceSetId, practiceAttemptId, [...(missedItemIds ?? [])].sort()])}`
    : null;
  const [restoredProgress] = useState(() => readReviewProgress(progressKey));
  const [reviewSessionId] = useState(() => restoredProgress?.sessionId ?? crypto.randomUUID());
  const [offset, setOffset] = useState(0);
  const { data: twin } = useTwin(courseId);
  const deckQuery = useFlashcardDeck(courseId, 20, skillId, mode, offset, { enabled: !practiceSetId });
  const practiceResults = usePracticeSetResults(courseId, practiceSetId ?? null, Boolean(practiceSetId), practiceAttemptId);
  const practiceCards = useMemo<FlashcardCard[] | null>(() => {
    if (!practiceSetId || !practiceResults.data) return null;
    const skillName = twin?.skills.find((skill) => skill.skillId === skillId)?.name ?? null;
    // This mode is scoped to one recap attempt. If the exact item IDs were
    // lost from navigation, fail closed instead of expanding to every missed
    // answer ever recorded against the saved set.
    const requestedMisses = new Set(missedItemIds ?? []);
    return practiceResults.data.questions
      .filter((question) => question.prompt !== null && requestedMisses.has(question.itemId))
      .map((question) => ({
        itemId: question.itemId,
        skillId: skillId ?? "",
        skillName,
        prompt: question.prompt ?? "Question unavailable",
        back: {
          label: question.correctAnswer?.text ?? null,
          explanation: question.explanation ?? "",
        },
        state: "due" as const,
        box: 0,
      }));
  }, [practiceSetId, missedItemIds, practiceResults.data, twin?.skills, skillId]);
  const practiceDeck = useMemo<FlashcardDeckData | undefined>(() => {
    if (!practiceSetId || !practiceCards) return undefined;
    return {
      courseId,
      cards: practiceCards,
      stats: { tracked: practiceCards.length, due: practiceCards.length, learning: 0, mastered: 0 },
      mode: "all",
      sessionId: reviewSessionId,
      offset: 0,
      limit: practiceCards.length,
      totalCards: practiceCards.length,
      hasMore: false,
    };
  }, [practiceSetId, practiceCards, courseId, reviewSessionId]);
  const data = practiceSetId ? practiceDeck : deckQuery.data;
  const isLoading = practiceSetId ? practiceResults.isLoading : deckQuery.isLoading;
  const isError = practiceSetId ? practiceResults.isError : deckQuery.isError;
  const isFetching = practiceSetId ? practiceResults.isFetching : deckQuery.isFetching;
  const refetch = practiceSetId ? practiceResults.refetch : deckQuery.refetch;
  const membership = useFlashcardMembership(courseId, skillId ?? "");
  const bank = useBankStatus(courseId);
  const review = useReviewFlashcard(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);

  const [index, setIndex] = useState(0);
  const [sessionCards, setSessionCards] = useState<FlashcardCard[] | null>(null);
  const [phase, setPhase] = useState<Phase>("front");
  const frontFaceRef = useRef<HTMLButtonElement>(null);
  const backFaceRef = useRef<HTMLButtonElement>(null);
  const moveFlipFocus = useRef(false);
  useEffect(() => {
    if (!moveFlipFocus.current) return;
    moveFlipFocus.current = false;
    (phase === "back" ? backFaceRef : frontFaceRef).current?.focus({ preventScroll: true });
  }, [phase]);
  const [deckDone, setDeckDone] = useState(false);
  const [isReplay, setIsReplay] = useState(false);
  const [ratingsByItemId, setRatingsByItemId] = useState<Record<string, boolean>>({});
  const [showReviewSpinner, setShowReviewSpinner] = useState(false);
  const [pendingRemembered, setPendingRemembered] = useState<boolean | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const [explainText, setExplainText] = useState<string | null>(null);
  const [hintAnimationKey, setHintAnimationKey] = useState<string | undefined>();
  const [explainAnimationKey, setExplainAnimationKey] = useState<string | undefined>();
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);
  const startedAtRef = useRef(Date.now());
  const replySequenceRef = useRef(0);
  const reviewInFlightRef = useRef(false);
  const postedRatingIdsRef = useRef(new Set<string>());
  const reviewIdempotencyRef = useRef<{
    itemId: string;
    remembered: boolean;
    key: string;
  } | null>(null);
  const initializedSessionRef = useRef<string | null>(null);
  const celebrationRoundRef = useRef(0);
  const markRef = useRef<((remembered: boolean) => void) | null>(null);
  const responseSessionKey = data?.sessionId ?? (data
    ? `${courseId}:${offset}:${data.cards.map((item) => item.itemId).join(",")}`
    : null);

  useEffect(() => {
    if (!data || responseSessionKey === initializedSessionRef.current) return;
    initializedSessionRef.current = responseSessionKey;
    const cardsById = new Map(data.cards.map((card) => [card.itemId, card]));
    const saved = restoredProgress;
    const valid = saved && saved.queue.every((id) => cardsById.has(id));
    setSessionCards(valid ? saved.queue.map((id) => cardsById.get(id)!) : data.cards);
    setIndex(valid ? saved.index : 0);
    setDeckDone(false);
    setIsReplay(false);
    postedRatingIdsRef.current = new Set(valid ? saved.posted : []);
    reviewIdempotencyRef.current = valid ? saved.pending : null;
    setRatingsByItemId(valid ? saved.ratings : {});
  }, [data, responseSessionKey, restoredProgress]);

  useEffect(() => {
    if (!review.isPending) {
      setShowReviewSpinner(false);
      return;
    }
    const timer = window.setTimeout(() => setShowReviewSpinner(true), 200);
    return () => window.clearTimeout(timer);
  }, [review.isPending]);

  useEffect(() => {
    contentEpochRef.current += 1;
    setPhase("front");
    setDeckDone(false);
    setHintText(null);
    setExplainText(null);
    setHintAnimationKey(undefined);
    setExplainAnimationKey(undefined);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    startedAtRef.current = Date.now();
  }, [index, data?.courseId, responseSessionKey]);

  const deckCards = sessionCards ?? data?.cards ?? [];
  const originalDeckLength = data?.cards.length ?? 0;
  const originalCardIds = new Set((data?.cards ?? []).map((item) => item.itemId));
  const reviewCounts = Object.values(ratingsByItemId).reduce(
    (counts, remembered) => remembered
      ? { ...counts, gotIt: counts.gotIt + 1 }
      : { ...counts, stillLearning: counts.stillLearning + 1 },
    { gotIt: 0, stillLearning: 0 },
  );
  useEffect(() => {
    if (!deckDone || practiceSetId || review.isPending || reduceMotion || originalCardIds.size === 0 || reviewCounts.gotIt !== originalCardIds.size) return;
    celebrateOnce(`study:${reviewSessionId}:${offset}:${celebrationRoundRef.current}`);
  }, [deckDone, practiceSetId, review.isPending, reduceMotion, reviewCounts.gotIt, originalCardIds.size, reviewSessionId, offset]);

  const activeItemId = deckCards[index]?.itemId;
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!activeItemId || event.repeat || event.altKey || event.ctrlKey || event.metaKey || deckDone || review.isPending) return;
      const target = event.target;
      if (target instanceof HTMLElement && (
        target.isContentEditable || target.closest("input, textarea, select, [contenteditable='true']")
      )) return;

      if (event.code === "Space") {
        event.preventDefault();
        moveFlipFocus.current = true;
        setPhase((current) => current === "front" ? "back" : "front");
        return;
      }
      if (phase !== "back" || review.isPending || reviewInFlightRef.current) return;
      if (event.key === "1") {
        event.preventDefault();
        markRef.current?.(false);
      } else if (event.key === "2") {
        event.preventDefault();
        markRef.current?.(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeItemId, deckDone, phase, review.isPending]);

  if (isLoading)
    return (<SessionState title="Study" onExit={onExit}>{<LoadingPanel label="Loading your cards…" lines={4} />}</SessionState>);
  if (isError)
    return (<SessionState title="Study" onExit={onExit}>{(
      <EmptyState
        title="We could not load flashcards"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    )}</SessionState>);
  if (practiceSetId && (!missedItemIds || missedItemIds.length === 0)) {
    return (<SessionState title="Study" onExit={onExit}>{(
      <EmptyState
        title="Missed questions are unavailable"
        description="Return to your results and open Review missed again."
        action={onReviewDone
          ? <Button variant="outline" onClick={() => onReviewDone(practiceSetId)}>Results</Button>
          : undefined}
      />
    )}</SessionState>);
  }
  if (practiceSetId && practiceCards?.length === 0) {
    return (<SessionState title="Study" onExit={onExit}>{(
      <EmptyState
        title="Missed questions are unavailable"
        description="Return to your results and open Review missed again."
        action={onReviewDone
          ? <Button variant="outline" onClick={() => onReviewDone(practiceSetId)}>Results</Button>
          : undefined}
      />
    )}</SessionState>);
  }
  const remainingToday = data?.newRemainingToday ?? data?.newCardsRemainingToday;
  const dailyNewCapReached = mode === "review" && remainingToday === 0 &&
    (membership.data?.counts.new ?? 0) > 0;
  if (!data || data.cards.length === 0) {
    const visibleSkills = bank.data?.skills.filter((entry) => !skillId || entry.skillId === skillId) ?? [];
    const selectedSkill = skillId
      ? visibleSkills[0]
      : visibleSkills.find((entry) => !entry.usable && entry.status !== "no_material");
    const noMaterial = bank.data?.bankServing === true && (
      skillId
        ? selectedSkill?.status === "no_material"
        : visibleSkills.length > 0 && visibleSkills.every((entry) => entry.status === "no_material")
    );
    const preparing = bank.data?.bankServing === true && !noMaterial && (
      skillId ? !selectedSkill || !selectedSkill.usable
        : visibleSkills.some((entry) => entry.status !== "no_material" && !entry.usable)
    );
    if (bank.isLoading) {
      return (<SessionState title="Study" onExit={onExit}>{<LoadingPanel label="Checking card availability…" lines={4} />}</SessionState>);
    }
    if (noMaterial) {
      return (<SessionState title="Study" onExit={onExit}>{(
        <EmptyState
          title="No course material yet"
          description={skillId
            ? "Your course team has not added material for this skill yet."
            : "Your course team has not added material for this course yet."}
        />
      )}</SessionState>);
    }
    if (preparing) {
      return (<SessionState title="Study" onExit={onExit}>{(
        <LoadingPanel
          label={`Preparing questions (${selectedSkill?.mcqReady ?? 0} of ${selectedSkill?.mcqTarget ?? 0})`}
          lines={4}
        />
      )}</SessionState>);
    }
    if (bank.isError) {
      return (<SessionState title="Study" onExit={onExit}>{(
        <EmptyState
          title="We could not check card availability"
          description="Check your connection and reload the deck."
          action={<Button variant="outline" onClick={() => refetch()}>Reload deck</Button>}
        />
      )}</SessionState>);
    }
    if (mode === "review" && remainingToday === 0 && skillId && membership.isLoading) {
      return (<SessionState title="Study" onExit={onExit}>{<LoadingPanel label="Checking your review cards…" lines={3} />}</SessionState>);
    }
    if (dailyNewCapReached) {
      return (<SessionState title="Study" onExit={onExit}>{(
        <EmptyState
          title="Daily new card limit reached"
          description="You've started 20 new cards today. Come back tomorrow, or use Study all."
        />
      )}</SessionState>);
    }
    const allCaughtUp = data ? data.stats.tracked > 0 : false;
    return (<SessionState title="Study" onExit={onExit}>{(
      <EmptyState
        title={allCaughtUp ? "All caught up" : "No cards yet"}
        description={
          allCaughtUp
            ? skillId
              ? "Nothing is due for review on this skill right now. Missed cards resurface sooner. Come back later or choose another topic."
              : "Nothing is due for review right now. Missed cards resurface sooner. Come back later."
            : skillId
              ? "No cards are available for this skill right now."
              : "No cards are available for this course right now."
        }
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Button variant="outline" onClick={() => void refreshEmptyDeck()} disabled={isFetching} aria-busy={isFetching}>
              {isFetching ? <Spinner aria-hidden /> : null}
              {isFetching ? "Checking cards…" : "Reload deck"}
            </Button>
            <Button variant="orange" onClick={onExit}>Back to Study</Button>
          </div>
        }
      />
    )}</SessionState>);
  }

  const total = originalCardIds.size;

  if (deckDone) {
    if (practiceSetId && onReviewDone) {
      return (
        <StudySurface
          bar={
            <SessionBar
              title="Reviewing missed questions"
              progress={{ current: total, total, label: "cards" }}
              onBack={() => onReviewDone(practiceSetId)}
              backLabel="Results"
            />
          }
        >
          <StudyStream>
            <LoadingPanel label="Returning to test results…" lines={2} />
          </StudyStream>
        </StudySurface>
      );
    }
    return (
      <StudySurface
        bar={
          <SessionBar
            title="Study"
            progress={{ current: total, total, label: "cards" }}
            onBack={() => practiceSetId && onReviewDone
              ? onReviewDone(practiceSetId)
              : onExit()}
            backLabel={practiceSetId && onReviewDone ? "Results" : "Choose another topic"}
          />
        }
        dock={
          <ComposeDock
            tourId="tour-study-dock"
            primary={{ label: "Go through these again", onClick: replayDeck, disabled: review.isPending, icon: RotateCCWIcon }}
            secondary={{ label: "Check for more cards", onClick: reloadDeck, disabled: review.isPending || isFetching, pending: isFetching, icon: ArrowRightIcon }}
          />
        }
      >
        <StudyStream>
          <div data-tour="study-complete" className="relative border bg-card p-6">
            <CornerBrackets />
            <p className="text-xs font-medium uppercase tracking-[0.06em] text-brand-slate">
              {isReplay ? "Practice complete" : "Study complete"}
            </p>
            <p className="mt-1.5 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              {total}<span className="text-muted-foreground">/{total}</span>
              <span className="ml-2 text-sm font-medium tracking-normal text-muted-foreground">{total === 1 ? "card" : "cards"} recalled</span>
            </p>
            <p className="mt-3 font-display text-lg font-semibold text-foreground">
              You recalled every card.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {isReplay
                ? "This practice round did not change your review schedule."
                : "You marked every card Got it in this session. Your next review follows your schedule."}
            </p>
            {mode === "all" && data.hasMore ? (
              <div className="mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={continueNextGroup}
                  aria-busy={isFetching || undefined}
                >
                  {isFetching ? <Spinner aria-hidden /> : null}
                  Continue with next 20
                </Button>
              </div>
            ) : null}
          </div>
        </StudyStream>
      </StudySurface>
    );
  }

  const card: FlashcardCard = deckCards[index];
  const isSecondLook = index >= originalDeckLength;

  function mark(remembered: boolean) {
    if (reviewInFlightRef.current) return;
    const alreadyPosted = postedRatingIdsRef.current.has(card.itemId);
    const shouldRequeue = !remembered;
    const queueBeforeRating = deckCards;
    const ratingIndex = index;
    const nextQueue = shouldRequeue ? [...queueBeforeRating, card] : queueBeforeRating;

    const priorRating = ratingsByItemId[card.itemId];
    const nextRatings = { ...ratingsByItemId, [card.itemId]: remembered };
    setRatingsByItemId(nextRatings);
    const distinctMissed = new Set((practiceCards ?? []).map((item) => item.itemId)).size;
    const stillLearningCount = Object.values(nextRatings).filter((rating) => !rating).length;
    const showMissedReviewToast = () => {
      toast.success(
        `Reviewed ${distinctMissed} missed ${distinctMissed === 1 ? "question" : "questions"}${stillLearningCount ? ` · ${stillLearningCount} still learning` : ""}`,
      );
    };
    if (shouldRequeue) {
      setSessionCards(nextQueue);
    }
    advanceToNext(ratingIndex, nextQueue.length);

    // The session contract records only the first rating for a card. A card
    // requeued after "Still learning" can be rated again locally without
    // writing a second item_reviews row.
    const persistAdvanced = () => writeReviewProgress(progressKey,
      ratingIndex + 1 >= nextQueue.length ? null : {
        sessionId: reviewSessionId,
        queue: nextQueue.map((item) => item.itemId),
        index: ratingIndex + 1,
        ratings: nextRatings,
        posted: [...postedRatingIdsRef.current],
        pending: null,
      });
    if (alreadyPosted) {
      persistAdvanced();
      if (practiceSetId && ratingIndex + 1 >= nextQueue.length) {
        showMissedReviewToast();
        onReviewDone?.(practiceSetId);
      }
      return;
    }

    reviewInFlightRef.current = true;
    setPendingRemembered(remembered);
    if (
      reviewIdempotencyRef.current?.itemId !== card.itemId ||
      reviewIdempotencyRef.current.remembered !== remembered
    ) {
      reviewIdempotencyRef.current = {
        itemId: card.itemId,
        remembered,
        key: crypto.randomUUID(),
      };
    }
    // A refresh during POST resumes the prior card with the same key. The
    // server can safely acknowledge the original write if it already landed.
    writeReviewProgress(progressKey, {
      sessionId: reviewSessionId,
      queue: queueBeforeRating.map((item) => item.itemId),
      index: ratingIndex,
      ratings: ratingsByItemId,
      posted: [...postedRatingIdsRef.current],
      pending: reviewIdempotencyRef.current,
    });
    review.mutate(
      {
        itemId: card.itemId,
        remembered,
        latencyMs: Date.now() - startedAtRef.current,
        sessionId: data?.sessionId ?? reviewSessionId,
        idempotencyKey: reviewIdempotencyRef.current.key,
      },
      {
        onSuccess: () => {
          reviewInFlightRef.current = false;
          setPendingRemembered(null);
          postedRatingIdsRef.current.add(card.itemId);
          reviewIdempotencyRef.current = null;
          persistAdvanced();
          if (practiceSetId && ratingIndex + 1 >= nextQueue.length) {
            showMissedReviewToast();
            onReviewDone?.(practiceSetId);
          }
        },
        onError: () => {
          reviewInFlightRef.current = false;
          setPendingRemembered(null);
          setSessionCards(queueBeforeRating);
          setIndex(ratingIndex);
          setDeckDone(false);
          setPhase("back");
          setRatingsByItemId((ratings) => {
            const reverted = { ...ratings };
            if (priorRating === undefined) delete reverted[card.itemId];
            else reverted[card.itemId] = priorRating;
            return reverted;
          });
          toast.error("Could not save your review. Try again.");
        },
      }
    );
  }

  function advanceToNext(currentIndex: number, queueLength: number) {
    if (currentIndex + 1 >= queueLength) {
      setDeckDone(true);
      return;
    }
    setIndex(currentIndex + 1);
  }

  async function refreshEmptyDeck() {
    const refreshed = await refetch();
    if (refreshed.isError || !refreshed.data || !("cards" in refreshed.data)) return;
    if (refreshed.data.cards.length === 0) {
      toast.info(refreshed.data.stats.tracked > 0
        ? "No cards are due yet. Return to Study to review all cards."
        : "No cards are available yet. Try again later.");
    }
  }

  function reloadDeck() {
    celebrationRoundRef.current += 1;
    setIsReplay(false);
    // A one-card deck already sits at index 0, so changing only the index
    // would not rerun the reset effect. Clear the terminal state explicitly.
    setDeckDone(false);
    setIndex(0);
    setPhase("front");
    setHintText(null);
    setExplainText(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setRatingsByItemId({});
    setSessionCards(data?.cards ?? []);
    postedRatingIdsRef.current.clear();
    refetch();
  }

  function replayDeck() {
    if (review.isPending || reviewInFlightRef.current) return;
    // Replay only the original session cards, in order, with no refetch.
    // Retain postedRatingIdsRef: every rating in this practice round stays
    // local, including any cards requeued after "Still learning".
    contentEpochRef.current += 1;
    setSessionCards(data?.cards ?? []);
    setIsReplay(true);
    setIndex(0);
    setDeckDone(false);
    setPhase("front");
    setRatingsByItemId({});
    setHintText(null);
    setExplainText(null);
    setHintAnimationKey(undefined);
    setExplainAnimationKey(undefined);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    startedAtRef.current = Date.now();
  }

  function continueNextGroup() {
    setIsReplay(false);
    setDeckDone(false);
    setIndex(0);
    setPhase("front");
    setHintText(null);
    setExplainText(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setOffset((current) => current + 20);
  }

  function askHint() {
    const requestEpoch = contentEpochRef.current;
    setHintText(null);
    setHintAnimationKey(`${courseId}:${replySessionId}:${card.itemId}:hint:${++replySequenceRef.current}`);
    hint.mutate(
      {
        question: `Give me a hint for this recall card without revealing the answer: "${card.prompt}"`,
        style: "eli5",
      },
      { onSuccess: (r) => { if (requestEpoch === contentEpochRef.current) setHintText(r.answer); } }
    );
  }

  function askExplain() {
    const requestEpoch = contentEpochRef.current;
    setExplainText(null);
    setExplainAnimationKey(`${courseId}:${replySessionId}:${card.itemId}:explain:${++replySequenceRef.current}`);
    explain.mutate(
      { question: `Explain this in more detail: ${card.prompt}`, style: "detail" },
      { onSuccess: (r) => { if (requestEpoch === contentEpochRef.current) setExplainText(r.answer); } }
    );
  }

  function askAboutCard(question: string) {
    const requestEpoch = contentEpochRef.current;
    setPendingFollowUp(question);
    followUp.mutate(
      {
        question: [
          "You are Kala helping a student study one flashcard.",
          "The card is a term/prompt with a definition/answer on the back. Guide recall without simply stating the back while they are still on the front; explain the concept clearly once they have flipped.",
          `Card prompt: ${card.prompt}`,
          `Card back: ${card.back.label ?? "Answer unavailable"}`,
          `Side shown: ${phase}.`,
          `Student question: ${question}`,
        ].join("\n\n"),
      },
      {
        onSuccess: (answer) => {
          if (requestEpoch !== contentEpochRef.current) return;
          setFollowUpTurns((turns) => [...turns, { question, answer: answer.answer }]);
          setPendingFollowUp(null);
        },
        onError: () => { if (requestEpoch === contentEpochRef.current) setPendingFollowUp(null); },
      }
    );
  }

  markRef.current = mark;

  const dockPrimary: ComposeDockPrimary = phase === "front"
    ? {
        id: "tour-study-show-answer",
        label: "Show answer",
        onClick: () => setPhase("back"),
        icon: ArrowRightIcon,
      }
    : {
        label: "Got it",
        onClick: () => mark(true),
        disabled: review.isPending,
        icon: showReviewSpinner && pendingRemembered === true ? ReviewSpinnerIcon : CheckIcon,
      };
  const dockSecondary: ComposeDockPrimary | undefined = phase === "back"
    ? {
        label: "Still learning",
        onClick: () => mark(false),
        disabled: review.isPending,
        icon: showReviewSpinner && pendingRemembered === false ? ReviewSpinnerIcon : RotateCCWIcon,
      }
    : undefined;

  return (
    <StudySurface
      bar={
        <SessionBar
          title={practiceSetId ? "Reviewing missed questions" : "Study"}
          progress={{ current: reviewCounts.gotIt, total, label: "recalled" }}
          onBack={() => practiceSetId && onReviewDone
            ? onReviewDone(practiceSetId)
            : onExit()}
          backLabel={practiceSetId && onReviewDone ? "Results" : "Choose another topic"}
        />
      }
      dock={
        <ComposeDock
          tourId="tour-study-dock"
          primary={practiceSetId && phase === "back" && index + 1 >= deckCards.length
            ? { ...dockPrimary, label: "Got it · Back to results" }
            : dockPrimary}
          secondary={dockSecondary}
          onAsk={phase === "back" ? askAboutCard : undefined}
          askPending={followUp.isPending}
          placeholder="Ask Kala about this card…"
        />
      }
    >
      <StudyStream>
        {isReplay ? (
          <p role="status" className="border-l-2 border-border px-3 py-2 text-sm text-muted-foreground">
            Practice round · Your review schedule will not change.
          </p>
        ) : null}
        {dailyNewCapReached ? (
          <p className="border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
            You&apos;ve started 20 new cards today. Come back tomorrow, or use Study all.
          </p>
        ) : null}
        {/* Deck state is session context, not a second panel header. */}
        <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-xs text-muted-foreground">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="min-w-0 truncate text-sm font-semibold text-foreground">
              {card.skillName ?? "Card"}
            </span>
            {practiceSetId ? null : <StateBadge state={ratingsByItemId[card.itemId] === false ? "slipping" : card.state} />}
            {isSecondLook ? (
              <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-sm border border-border bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold text-foreground">
                <RotateCCWIcon size={12} aria-hidden />
                Second look
              </span>
            ) : null}
          </div>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${card.itemId}:${index}`}
            initial={reduceMotion ? false : { opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduceMotion ? { opacity: 1, x: 0 } : { opacity: 0, x: -28 }}
            transition={{ duration: reduceMotion ? 0 : 0.22, ease: "easeOut" }}
            className="relative border bg-card"
          >
          <CornerBrackets />

          {/* A real 3D flip, not a content swap. The wrapper supplies the
              perspective; the inner element is the thing that rotates and
              carries preserve-3d so its two faces keep their own 3D space. The
              faces are stacked in ONE grid cell (grid-area 1/1) so the card
              sizes to whichever side is taller — absolutely positioning them
              would collapse the container to zero height. Each face hides its
              backface and the back is pre-rotated, so only the correct side is
              ever visible.

              Both entry points (tapping the card, and the dock's "Show
              answer") set the same phase, so they drive the identical
              rotation rather than one animating and one snapping.

              Reduced motion: the transform transition is dropped entirely, so
              the flip degrades to the instant swap it has always been, rather
              than forcing a rotation on someone who asked for less of it. */}
          <div className="[perspective:1400px] px-5 py-5">
            <div
              className={cn(
                "grid [transform-style:preserve-3d]",
                !reduceMotion &&
                  "transition-transform duration-500 [transition-timing-function:cubic-bezier(0.2,0.8,0.25,1)]"
              )}
              style={{ transform: phase === "back" ? "rotateY(180deg)" : "rotateY(0deg)" }}
            >
              {/* front — the prompt, the recall beat. Tapping flips; flipping
                  is free and costs no schedule. */}
              <button
                type="button"
                ref={frontFaceRef}
                onClick={() => { moveFlipFocus.current = true; setPhase("back"); }}
                inert={phase === "back"}
                tabIndex={phase === "back" ? -1 : 0}
                className="block w-full space-y-5 text-left [backface-visibility:hidden] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [grid-area:1/1]"
              >
                <p className="text-lg font-medium leading-relaxed text-foreground">
                  {card.prompt}
                </p>
                <div className="flex items-center justify-between gap-4">
                  <p className="text-xs text-muted-foreground">
                    Recall the answer, then flip to check yourself.
                  </p>
                  <span className="font-mono text-xs text-muted-foreground">tap to flip</span>
                </div>
              </button>

              {/* The back shows the answer; grading lives in the persistent dock. */}
              <button
                type="button"
                ref={backFaceRef}
                inert={phase !== "back"}
                tabIndex={phase === "back" ? 0 : -1}
                aria-label="Flip to question"
                disabled={phase !== "back"}
                onClick={() => { moveFlipFocus.current = true; setPhase("front"); }}
                className="block w-full space-y-4 text-left [backface-visibility:hidden] [grid-area:1/1] [transform:rotateY(180deg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <p className="text-sm text-muted-foreground">{card.prompt}</p>
                <div className="rounded-sm border border-brand-green/40 bg-brand-green/10 px-3 py-2.5">
                  {/* solid token, not a /70 alpha: the low-opacity label on a
                      tinted background was the lowest-contrast text on the
                      screen. "Answer" is a real label and must be readable. */}
                  <p className="text-xs font-medium uppercase tracking-wide text-foreground">
                    Answer
                  </p>
                  <p className="mt-0.5 text-base font-semibold text-foreground">
                    {card.back.label ?? <span className="italic text-muted-foreground">Answer unavailable</span>}
                  </p>
                </div>
                {card.back.explanation ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {card.back.explanation}
                  </p>
                ) : null}

              </button>
            </div>
          </div>
          </motion.div>
        </AnimatePresence>
        {/* Ask-for-help row. These stay as plain text affordances rather than
            buttons competing with the dock's primary action, because they
            trigger distinct TUTOR STYLES (a nudge, a deep explanation) that
            the free-text compose box cannot express. Their output lands as a
            bubble in the thread below — see the thread block — instead of
            inside the card, so this reads as one conversation with Kala rather
            than a card with a text dump stuffed into it. */}
        <div className="flex items-center gap-4 text-xs">
          {phase === "front" ? (
            <button
              type="button"
              onClick={askHint}
              disabled={hint.isPending}
              className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground underline underline-offset-4 transition-colors hover:text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {hint.isPending ? <Spinner className="size-3.5" aria-hidden /> : <BrainIcon size={14} aria-hidden />}
              {hint.isPending ? "Thinking…" : "Give me a hint"}
            </button>
          ) : null}
          {phase === "back" ? (
            <button
              type="button"
              onClick={askExplain}
              disabled={explain.isPending}
              className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground underline underline-offset-4 transition-colors hover:text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {explain.isPending ? <Spinner className="size-3.5" aria-hidden /> : <SparklesIcon size={14} aria-hidden />}
              {explain.isPending ? "Thinking…" : "Explain more"}
            </button>
          ) : null}
        </div>

        {/* Kala's thread for this card: the hint/explanation turn, then any
            free-text follow-ups from the dock. Rendered as the same
            UserBlock/AssistantBlock bubbles LessonChat uses, so every surface
            talks the same way. */}
        {hintText || hint.isPending || explainText || explain.isPending ? (
          <div className="space-y-5 border-t pt-5">
            {hintText || hint.isPending ? (
              <AssistantBlock
                text={hintText ?? undefined}
                pending={hint.isPending}
                pendingLabel="Kala is preparing a hint…"
                animationKey={hintAnimationKey}
              />
            ) : null}
            {explainText || explain.isPending ? (
              <AssistantBlock
                text={explainText ?? undefined}
                pending={explain.isPending}
                pendingLabel="Kala is preparing an explanation…"
                animationKey={explainAnimationKey}
              />
            ) : null}
          </div>
        ) : null}

        {followUpTurns.map((turn, turnIndex) => (
          <div key={`${turn.question}-${turnIndex}`} className="space-y-3">
            <UserBlock text={turn.question} />
            <AssistantBlock
              id={turnIndex === 0 ? "tour-study-reply" : undefined}
              text={turn.answer}
              animationKey={`${courseId}:${replySessionId}:${card.itemId}:follow-up:${turnIndex}`}
            />
          </div>
        ))}
        {pendingFollowUp ? (
          <div className="space-y-3">
            <UserBlock text={pendingFollowUp} />
            <AssistantBlock pending pendingLabel="Kala is thinking…" />
          </div>
        ) : null}
      </StudyStream>
    </StudySurface>
  );
}
