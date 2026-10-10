import { forwardRef, useEffect, useId, useImperativeHandle, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { BrainIcon } from "@/components/ui/brain";
import { SparklesIcon } from "@/components/ui/sparkles";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock, type ComposeDockPrimary } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";
import { UserBlock } from "@/components/study/UserBlock";
import { CornerBrackets, MasteryBand } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { CheckIcon } from "@/components/ui/check";
import { RotateCCWIcon } from "@/components/ui/rotate-ccw";
import { Spinner } from "@/components/ui/spinner";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { cn } from "@/lib/utils";
import { useFlashcardDeck, useReviewFlashcard } from "@/features/flashcards/hooks/use-flashcards";
import { useCreateSetFromItems } from "@/features/practice";
import { useBankStatus } from "@/features/bank";
import { useTwin } from "@/features/twin";
import { useTutorAsk } from "@/features/tutor";
import type { FlashcardCard } from "@/features/flashcards/schema/flashcards.schema";

// Study mode: a flip card, not a quiz. Front shows the prompt, tapping flips
// to the back (answer label + explanation), and the student marks it "Got it"
// or "Review again" themselves. That self-mark advances the spaced-repetition
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

function StateBadge({ state }: { state: "due" | "new" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 text-[10.5px] font-semibold text-foreground",
        state === "due" ? "border-brand-orange/50 bg-brand-orange/10" : "border-border bg-muted"
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-sm",
          state === "due" ? "bg-brand-orange" : "bg-muted-foreground/60"
        )}
      />
      {state === "due" ? "Due" : "New"}
    </span>
  );
}

export function FlashcardDeck({
  courseId,
  skillId,
  onExit,
}: {
  courseId: string;
  skillId?: string;
  onExit: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const replySessionId = useId();
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useFlashcardDeck(courseId, 10, skillId);
  const bank = useBankStatus(courseId);
  const review = useReviewFlashcard(courseId);
  const testMe = useCreateSetFromItems(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);
  const { data: twin } = useTwin(courseId);

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("front");
  const [deckDone, setDeckDone] = useState(false);
  const [reviewCounts, setReviewCounts] = useState({ gotIt: 0, reviewAgain: 0 });
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
  const markRef = useRef<((remembered: boolean) => void) | null>(null);

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

  useEffect(() => {
    setReviewCounts({ gotIt: 0, reviewAgain: 0 });
  }, [courseId, skillId]);

  const activeItemId = data?.cards[index]?.itemId;
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!activeItemId || event.repeat || event.altKey || event.ctrlKey || event.metaKey || deckDone) return;
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
          <Button variant="outline" onClick={() => refetch()}>Reload deck</Button>
        }
      />
    );
  }

  const total = data.cards.length;

  if (deckDone) {
    const canTest = Boolean(skillId) && data.cards.length > 0;
    return (
      <StudySurface
        bar={
          <SessionBar
            title="Study"
            progress={{ current: total, total, label: "cards" }}
            onBack={onExit}
            backLabel="Choose another topic"
          />
        }
        dock={
          <ComposeDock
            primary={
              canTest
                ? {
                    label: testMe.isPending ? "Building your test…" : "Test me on these",
                    onClick: testMeOnThese,
                    disabled: testMe.isPending,
                    icon: ArrowRightIcon,
                  }
                : { label: "Reload deck", onClick: reloadDeck, icon: ArrowRightIcon }
            }
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
              Nice work on {total} cards
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Missed cards resurface sooner, so your next pass is exactly what your schedule says
              you need.
            </p>
            <p className="mt-3 text-sm font-medium text-foreground">
              {reviewCounts.gotIt} got it, {reviewCounts.reviewAgain} coming back sooner.
            </p>
            {canTest ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Ready to prove it? A test on these same cards is graded, and it moves your
                mastery. Studying alone does not.
              </p>
            ) : null}
            <div className="mt-4">
              <Button variant="outline" size="sm" onClick={reloadDeck}>
                Reload deck
              </Button>
            </div>
          </div>
        </StudyStream>
      </StudySurface>
    );
  }

  const card: FlashcardCard = data.cards[index];
  const band = twin?.skills.find((s) => s.skillId === card.skillId)?.band;

  function mark(remembered: boolean) {
    if (reviewInFlightRef.current) return;
    reviewInFlightRef.current = true;
    setPendingRemembered(remembered);
    review.mutate(
      {
        itemId: card.itemId,
        remembered,
        latencyMs: Date.now() - startedAtRef.current,
      },
      {
        onSuccess: () => {
          reviewInFlightRef.current = false;
          setPendingRemembered(null);
          setReviewCounts((counts) => remembered
            ? { ...counts, gotIt: counts.gotIt + 1 }
            : { ...counts, reviewAgain: counts.reviewAgain + 1 });
          nextCard();
        },
        onError: () => {
          reviewInFlightRef.current = false;
          setPendingRemembered(null);
          toast.error("Could not save your review. Try again.");
        },
      }
    );
  }

  function nextCard() {
    if (index + 1 >= total) {
      setDeckDone(true);
      return;
    }
    setIndex((i) => i + 1);
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
    setReviewCounts({ gotIt: 0, reviewAgain: 0 });
    refetch();
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
          `Card back: ${card.back.label ?? "No answer label"}`,
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
        label: "Review again",
        onClick: () => mark(false),
        disabled: review.isPending,
        icon: showReviewSpinner && pendingRemembered === false ? ReviewSpinnerIcon : RotateCCWIcon,
      }
    : undefined;

  return (
    <StudySurface
      bar={
        <SessionBar
          title="Study"
          progress={{ current: index + 1, total, label: "card" }}
          onBack={onExit}
          backLabel="Choose another topic"
        />
      }
      dock={
        <ComposeDock
          primary={dockPrimary}
          secondary={dockSecondary}
          onAsk={phase === "back" ? askAboutCard : undefined}
          askPending={followUp.isPending}
          placeholder="Ask Kala about this card…"
        />
      }
    >
      <StudyStream>
        {/* Deck state is session context, not a second panel header. */}
        <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-xs text-muted-foreground">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="truncate text-sm font-semibold text-foreground">
              {card.skillName ?? "Card"}
            </span>
            {band ? <MasteryBand band={band} /> : null}
            <StateBadge state={card.state} />
          </div>
        </div>

        <div className="relative border bg-card">
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
                    {card.back.label ?? "No answer label"}
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
        </div>
        {/* Ask-for-help row. These stay as plain text affordances rather than
            buttons competing with the dock's primary action, because they
            trigger distinct TUTOR STYLES (a nudge, a deep explanation) that
            the free-text compose box cannot express. Their output lands as a
            bubble in the thread below — see the thread block — instead of
            inside the card, so this reads as one conversation with Kala rather
            than a card with a text dump stuffed into it. */}
        {phase === "back" || hintText || explainText || hint.isPending || explain.isPending ? (
          <div className="flex items-center gap-4 text-xs">
            <button
              type="button"
              onClick={askHint}
              disabled={hint.isPending}
              className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground transition-colors hover:text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <BrainIcon size={14} aria-hidden />
              {hint.isPending ? "Thinking…" : "Give me a hint"}
            </button>
            <button
              type="button"
              onClick={askExplain}
              disabled={explain.isPending}
              className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground transition-colors hover:text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <SparklesIcon size={14} aria-hidden />
              {explain.isPending ? "Thinking…" : "Explain more"}
            </button>
          </div>
        ) : null}

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
