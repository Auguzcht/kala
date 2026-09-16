import { useEffect, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { BrainIcon } from "@/components/ui/brain";
import { SparklesIcon } from "@/components/ui/sparkles";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock } from "@/components/study/ComposeDock";
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
import { apiErrorReason } from "@/lib/api-error";
import { useTwin } from "@/features/twin";
import { useTutorAsk } from "@/features/tutor";
import type {
  FlashcardCard,
  FlashcardReviewResult,
} from "@/features/flashcards/schema/flashcards.schema";

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
// (student decides, moves only the schedule). Same generated item underneath,
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
          "size-1.5 rounded-full",
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
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useFlashcardDeck(courseId, 10, skillId);
  const review = useReviewFlashcard(courseId);
  const testMe = useCreateSetFromItems(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);
  const { data: twin } = useTwin(courseId);

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("front");
  const [deckDone, setDeckDone] = useState(false);
  const [result, setResult] = useState<FlashcardReviewResult | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const [explainText, setExplainText] = useState<string | null>(null);
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);
  const startedAtRef = useRef(Date.now());

  useEffect(() => {
    setPhase("front");
    setDeckDone(false);
    setResult(null);
    setHintText(null);
    setExplainText(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    startedAtRef.current = Date.now();
  }, [index, data?.courseId]);

  if (isLoading)
    return <LoadingPanel label="Building your deck — Kala is writing the first cards…" lines={4} />;
  if (isError)
    return (
      <EmptyState
        title="We could not load flashcards"
        description={apiErrorReason(error) ?? "Check your connection and try again."}
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (!data || data.cards.length === 0) {
    const allCaughtUp = data ? data.stats.tracked > 0 : false;
    return (
      <EmptyState
        title={allCaughtUp ? "All caught up" : "No cards yet"}
        description={
          allCaughtUp
            ? skillId
              ? "Nothing is due for review on this skill right now. Missed cards resurface sooner — come back later, or choose another topic."
              : "Nothing is due for review right now. Missed cards resurface sooner — come back later."
            : skillId
              ? "This skill hasn't been mapped for flashcards yet."
              : "Skills for this course haven't been mapped yet."
        }
        action={
          <Button variant="outline" onClick={() => refetch()}>
            Refresh
          </Button>
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
            {canTest ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Ready to prove it? A test on these same cards is graded, and it moves your
                mastery — studying alone doesn't.
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
    review.mutate(
      {
        itemId: card.itemId,
        remembered,
        latencyMs: Date.now() - startedAtRef.current,
      },
      { onSuccess: (r) => setResult(r) }
    );
  }

  function nextCard() {
    if (index + 1 >= total) {
      setDeckDone(true);
      refetch();
      return;
    }
    setIndex((i) => i + 1);
  }

  function reloadDeck() {
    // A one-card deck already sits at index 0, so changing only the index
    // would not rerun the reset effect. Clear the terminal state explicitly.
    setDeckDone(false);
    setIndex(0);
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
          `Card back: ${card.back.label ?? "—"}`,
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

  const marked = result !== null;
  const atEnd = index + 1 >= total;
  const dockPrimary = !marked
    ? {
        label: phase === "front" ? "Show answer" : "Mark it to continue",
        onClick: phase === "front" ? () => setPhase("back") : () => {},
        disabled: phase === "back",
        icon: ArrowRightIcon,
      }
    : {
        label: atEnd ? "See recap" : "Next card",
        onClick: nextCard,
        icon: ArrowRightIcon,
      };

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
          <span className="shrink-0 font-mono text-xs text-muted-foreground">
            box {card.box}
          </span>
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

              {/* back — the answer, then the self-mark. This is the study move:
                  the student decides, and that decision drives the schedule. */}
              <div
                aria-hidden={phase !== "back"}
                className="space-y-4 [backface-visibility:hidden] [grid-area:1/1] [transform:rotateY(180deg)]"
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
                    {card.back.label ?? "—"}
                  </p>
                </div>
                {card.back.explanation ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {card.back.explanation}
                  </p>
                ) : null}

                {!marked ? (
                  <div className="flex flex-wrap gap-2.5 border-t pt-4">
                    <Button
                      variant="orange"
                      size="sm"
                      onClick={() => mark(true)}
                      disabled={review.isPending}
                    >
                      {review.isPending ? (
                        <Spinner className="size-3.5" />
                      ) : (
                        <CheckIcon size={15} aria-hidden />
                      )}
                      Got it
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => mark(false)}
                      disabled={review.isPending}
                    >
                      <RotateCCWIcon size={15} aria-hidden />
                      Review again
                    </Button>
                  </div>
                ) : (
                  <>
                    <p
                      className={cn(
                        "border-t pt-4 text-sm font-semibold",
                        result?.remembered ? "text-brand-green" : "text-brand-orange",
                      )}
                    >
                      {result?.remembered
                        ? "Marked as remembered."
                        : "Marked for review — this card comes back sooner."}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-xs text-muted-foreground">
                      <span>
                        next review in{" "}
                        {result && result.dueInHours < 24
                          ? `${result.dueInHours}h`
                          : `${Math.round((result?.dueInHours ?? 0) / 24)}d`}
                      </span>
                      <span>box {result?.box}</span>
                      {result?.graduated ? (
                        <span className="text-brand-green">graduated ✓</span>
                      ) : null}
                    </div>
                  </>
                )}
              </div>
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
        {phase === "back" ? (
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

        {result ? (
          <p className="text-right font-mono text-xs text-muted-foreground">
            {result.reward.streakDays}-day streak · {result.reward.xp} XP
          </p>
        ) : null}

        {/* Kala's thread for this card: the hint/explanation turn, then any
            free-text follow-ups from the dock. Rendered as the same
            UserBlock/AssistantBlock bubbles LessonChat uses, so every surface
            talks the same way. */}
        {hintText || explainText || hint.isPending || explain.isPending ? (
          <div className="border-t pt-5">
            <AssistantBlock
              text={hintText ?? explainText ?? undefined}
              pending={hint.isPending || explain.isPending}
              pendingLabel={
                hint.isPending ? "Kala is preparing a hint…" : "Kala is preparing an explanation…"
              }
              animate={false}
            />
          </div>
        ) : null}

        {followUpTurns.map((turn, turnIndex) => (
          <div key={`${turn.question}-${turnIndex}`} className="space-y-3">
            <UserBlock text={turn.question} />
            <AssistantBlock text={turn.answer} />
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
