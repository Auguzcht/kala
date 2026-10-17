import { forwardRef, useEffect, useId, useImperativeHandle, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
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
import { cn } from "@/lib/utils";
import {
  useFlashcardDeck,
  useFlashcardMembership,
  useReviewFlashcard,
} from "@/features/flashcards/hooks/use-flashcards";
import { useCreateSetFromItems, usePracticeSetResults } from "@/features/practice";
import { useBankStatus } from "@/features/bank";
import { useTwin } from "@/features/twin";
import { useTutorAsk } from "@/features/tutor";
import type { FlashcardCard, FlashcardDeck as FlashcardDeckData } from "@/features/flashcards/schema/flashcards.schema";
import { cardStatePresentation } from "@/features/flashcards/lib/card-state";

// Study mode: a flip card, not a quiz. Front shows the prompt, tapping flips
// to the back (answer label + explanation), and the student marks it "Got it"
// or "Still learning" themselves. That self-mark advances the spaced-repetition
// schedule so weak cards resurface sooner, but it does NOT feed the twin —
// self-report is not assessment (see routers/flashcards.py). To turn what you
// studied into a mastery signal, "Test me on these" hands the same skill to
// the graded quiz surface.
//
// The contrast with PracticePanel is the whole point of the split: practice is
// a graded MCQ (server decides correctness, moves mastery), study is a flip
// (student decides, moves only the schedule). Same question underneath,
// two honest modes.
//
// One topic choice per session (Stage 3 of the AI overhaul,
// docs/AI_OVERHAUL_TODO.md), but NOT one required skill — `skillId` stays
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
  missedItemIds,
  onReviewDone,
  onExit,
}: {
  courseId: string;
  skillId?: string;
  mode?: "review" | "all";
  /** When present, study only the questions missed in this saved test set. */
  practiceSetId?: string;
  /** Exact missed items from the recap attempt that opened this review. */
  missedItemIds?: string[];
  /** Return to the saved test recap after the missed items are reviewed. */
  onReviewDone?: (setId: string) => void;
  onExit: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const replySessionId = useId();
  const [reviewSessionId] = useState(() => crypto.randomUUID());
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();
  const { data: twin } = useTwin(courseId);
  const deckQuery = useFlashcardDeck(courseId, 20, skillId, mode, offset, { enabled: !practiceSetId });
  const practiceResults = usePracticeSetResults(courseId, practiceSetId ?? null, Boolean(practiceSetId));
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
      sessionId: practiceSetId,
      offset: 0,
      limit: practiceCards.length,
      totalCards: practiceCards.length,
      hasMore: false,
    };
  }, [practiceSetId, practiceCards, courseId]);
  const data = practiceSetId ? practiceDeck : deckQuery.data;
  const isLoading = practiceSetId ? practiceResults.isLoading : deckQuery.isLoading;
  const isError = practiceSetId ? practiceResults.isError : deckQuery.isError;
  const isFetching = practiceSetId ? practiceResults.isFetching : deckQuery.isFetching;
  const refetch = practiceSetId ? practiceResults.refetch : deckQuery.refetch;
  const membership = useFlashcardMembership(courseId, skillId ?? "");
  const bank = useBankStatus(courseId);
  const review = useReviewFlashcard(courseId);
  const testMe = useCreateSetFromItems(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);

  const [index, setIndex] = useState(0);
  const [sessionCards, setSessionCards] = useState<FlashcardCard[] | null>(null);
  const [phase, setPhase] = useState<Phase>("front");
  const [deckDone, setDeckDone] = useState(false);
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
  const markRef = useRef<((remembered: boolean) => void) | null>(null);
  const responseSessionKey = data?.sessionId ?? (data
    ? `${courseId}:${offset}:${data.cards.map((item) => item.itemId).join(",")}`
    : null);

  useEffect(() => {
    if (!data || responseSessionKey === initializedSessionRef.current) return;
    initializedSessionRef.current = responseSessionKey;
    setSessionCards(data.cards);
    setIndex(0);
    setDeckDone(false);
    postedRatingIdsRef.current.clear();
    setRatingsByItemId({});
  }, [data, responseSessionKey]);

  useEffect(() => {
    if (!review.isPending) {
      setShowReviewSpinner(false);
      return;
    }
    const timer = window.setTimeout(() => setShowReviewSpinner(true), 200);
    return () => window.clearTimeout(timer);
  }, [review.isPending]);

  useEffect(() => {
    setPhase("front");
    setDeckDone(false);
    setHintText(null);
    setExplainText(null);
    setHintAnimationKey(undefined);
    setExplainAnimationKey(undefined);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    startedAtRef.current = Date.now();
  }, [index, data?.courseId]);

  const deckCards = sessionCards ?? data?.cards ?? [];
  const originalDeckLength = data?.cards.length ?? 0;
  const originalCardIds = new Set((data?.cards ?? []).map((item) => item.itemId));
  const reviewCounts = Object.values(ratingsByItemId).reduce(
    (counts, remembered) => remembered
      ? { ...counts, gotIt: counts.gotIt + 1 }
      : { ...counts, stillLearning: counts.stillLearning + 1 },
    { gotIt: 0, stillLearning: 0 },
  );
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
    return <LoadingPanel label="Loading your cards…" lines={4} />;
  if (isError)
    return (
      <EmptyState
        title="We could not load flashcards"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (practiceSetId && (!missedItemIds || missedItemIds.length === 0)) {
    return (
      <EmptyState
        title="Missed questions are unavailable"
        description="Return to your results and open Review missed again."
        action={onReviewDone
          ? <Button variant="outline" onClick={() => onReviewDone(practiceSetId)}>Results</Button>
          : undefined}
      />
    );
  }
  if (practiceSetId && practiceCards?.length === 0) {
    return (
      <EmptyState
        title="Missed questions are unavailable"
        description="Return to your results and open Review missed again."
        action={onReviewDone
          ? <Button variant="outline" onClick={() => onReviewDone(practiceSetId)}>Results</Button>
          : undefined}
      />
    );
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
      !selectedSkill || !selectedSkill.usable
    );
    if (bank.isLoading) {
      return <LoadingPanel label="Checking card availability…" lines={4} />;
    }
    if (noMaterial) {
      return (
        <EmptyState
          title="No course material yet"
          description={skillId
            ? "This skill doesn&apos;t have course material yet."
            : "No mapped skill has course material yet."}
        />
      );
    }
    if (preparing) {
      return (
        <LoadingPanel
          label={`Preparing questions (${selectedSkill?.mcqReady ?? 0} of ${selectedSkill?.mcqTarget ?? 0})`}
          lines={4}
        />
      );
    }
    if (bank.isError) {
      return (
        <EmptyState
          title="We could not check card availability"
          description="Check your connection and reload the deck."
          action={<Button variant="outline" onClick={() => refetch()}>Reload deck</Button>}
        />
      );
    }
    if (mode === "review" && remainingToday === 0 && skillId && membership.isLoading) {
      return <LoadingPanel label="Checking your review cards…" lines={3} />;
    }
    if (dailyNewCapReached) {
      return (
        <EmptyState
          title="Daily new card limit reached"
          description="You've started 20 new cards today. Come back tomorrow, or use Study all."
        />
      );
    }
    const allCaughtUp = data ? data.stats.tracked > 0 : false;
    return (
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
    );
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
    const canTest = Boolean(skillId) && data.cards.length > 0;
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
            primary={{ label: "Return to menu", onClick: onExit, icon: ArrowRightIcon }}
            secondary={canTest ? {
              label: testMe.isPending ? "Building your test…" : "Test me on these",
              onClick: testMeOnThese,
              disabled: testMe.isPending,
              pending: testMe.isPending,
              icon: ArrowRightIcon,
            } : undefined}
          />
        }
      >
        <StudyStream>
          <div className="relative border bg-card p-6">
            <CornerBrackets />
            <p className="text-xs font-medium uppercase tracking-[0.06em] text-brand-slate">
              Deck complete
            </p>
            <p className="mt-1.5 font-display text-lg font-semibold text-foreground">
              You recalled all {total} {total === 1 ? "card" : "cards"}.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              You marked every card Got it in this session. Your next review follows your schedule.
            </p>
            {canTest ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Ready to prove it? A test on these same cards is graded, and it moves your
                mastery. Studying alone does not.
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={reloadDeck}>
                Reload deck
              </Button>
              {mode === "all" && data.hasMore ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={continueNextGroup}
                >
                  Continue with next 20
                </Button>
              ) : null}
            </div>
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
    if (alreadyPosted) {
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

  function continueNextGroup() {
    setDeckDone(false);
    setIndex(0);
    setPhase("front");
    setHintText(null);
    setExplainText(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setOffset((current) => current + 20);
  }

  // The study -> test bridge. Groups the exact cards just studied into a quiz
  // set (no regeneration) and enters test mode on it. Only offered for a
  // single-skill deck: a set is per-skill, so the cross-skill "review what's
  // due" deck has no one topic to test against.
  function testMeOnThese() {
    if (!data || !skillId) return;
    testMe.mutate(
      data.cards.map((c) => c.itemId),
      {
        onSuccess: (set) => {
          if (!set.setId) return;
          navigate({
            to: "/course/practice",
            search: { skillId, setId: set.setId },
          });
        },
      }
    );
  }

  function askHint() {
    setHintText(null);
    setHintAnimationKey(`${courseId}:${replySessionId}:${card.itemId}:hint:${++replySequenceRef.current}`);
    hint.mutate(
      {
        question: `Give me a hint for this recall card without revealing the answer: "${card.prompt}"`,
        style: "eli5",
      },
      { onSuccess: (r) => setHintText(r.answer) }
    );
  }

  function askExplain() {
    setExplainText(null);
    setExplainAnimationKey(`${courseId}:${replySessionId}:${card.itemId}:explain:${++replySequenceRef.current}`);
    explain.mutate(
      { question: `Explain this in more detail: ${card.prompt}`, style: "detail" },
      { onSuccess: (r) => setExplainText(r.answer) }
    );
  }

  function askAboutCard(question: string) {
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
          setFollowUpTurns((turns) => [...turns, { question, answer: answer.answer }]);
          setPendingFollowUp(null);
        },
        onError: () => setPendingFollowUp(null),
      }
    );
  }

  markRef.current = mark;

  const dockPrimary: ComposeDockPrimary = phase === "front"
    ? {
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
            {practiceSetId ? null : <StateBadge state={card.state} />}
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
                onClick={() => setPhase("back")}
                aria-hidden={phase === "back"}
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
                aria-hidden={phase !== "back"}
                tabIndex={phase === "back" ? 0 : -1}
                aria-label="Flip to question"
                disabled={phase !== "back"}
                onClick={() => setPhase("front")}
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
