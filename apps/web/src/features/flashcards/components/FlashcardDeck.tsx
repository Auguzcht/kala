import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { TransitionPanel } from "@/components/motion/transition-panel";
import { BrainIcon } from "@/components/ui/brain";
import { EyeIcon } from "@/components/ui/eye";
import { SparklesIcon } from "@/components/ui/sparkles";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";
import { UserBlock } from "@/components/study/UserBlock";
import { CornerBrackets, MasteryBand, bandFor } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { cn } from "@/lib/utils";
import { useFlashcardDeck, useRevealFlashcard, useReviewFlashcard } from "@/features/flashcards/hooks/use-flashcards";
import { useTwin } from "@/features/twin";
import { useTutorAsk } from "@/features/tutor";
import type {
  FlashcardCard,
  FlashcardReviewResult,
  FlashcardRevealResult,
} from "@/features/flashcards/schema/flashcards.schema";

// Spaced-repetition recall quiz: prompt first (a think beat), then options,
// then Hint / Reveal / Explain as separate actions — matching the target
// design (Flashcards.dc.html). Grading is server-side; Reveal is a committed
// lapse, so a revealed card is terminal for this render (no follow-up review
// call — see routers/flashcards.py). Session chrome comes from StudySurface;
// question + grading stays in AnswerableCard.
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

type Phase = "think" | "choose" | "answered" | "revealed";
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
  const { data, isLoading, isError, refetch } = useFlashcardDeck(courseId, 10, skillId);
  const review = useReviewFlashcard(courseId);
  const reveal = useRevealFlashcard(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);
  const { data: twin } = useTwin(courseId);

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("think");
  const [deckDone, setDeckDone] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [result, setResult] = useState<FlashcardReviewResult | null>(null);
  const [revealResult, setRevealResult] = useState<FlashcardRevealResult | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const [explainText, setExplainText] = useState<string | null>(null);
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);
  const hintsUsedRef = useRef(0);
  const startedAtRef = useRef(Date.now());

  useEffect(() => {
    setPhase("think");
    setDeckDone(false);
    setSelectedChoice(null);
    setResult(null);
    setRevealResult(null);
    setHintText(null);
    setExplainText(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
  }, [index, data?.courseId]);

  if (isLoading)
    return <LoadingPanel label="Building your deck — Kala is writing the first cards…" lines={4} />;
  if (isError)
    return (
      <EmptyState
        title="We could not load flashcards"
        description="Check your connection and try again."
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
    return (
      <StudySurface
        bar={
          <SessionBar
            title="Flashcards"
            progress={{ current: total, total, label: "cards" }}
            onBack={onExit}
            backLabel="Choose another topic"
          />
        }
        dock={
          <ComposeDock
            primary={{ label: "Reload deck", onClick: reloadDeck, icon: ArrowRightIcon }}
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
          </div>
        </StudyStream>
      </StudySurface>
    );
  }

  const card: FlashcardCard = data.cards[index];
  const band = twin?.skills.find((s) => s.skillId === card.skillId)?.band;

  const phaseIndex = phase === "think" ? 0 : phase === "choose" ? 1 : phase === "answered" ? 2 : 3;

  function answer(choiceId: string) {
    setSelectedChoice(choiceId);
    review.mutate(
      {
        itemId: card.itemId,
        choiceId,
        latencyMs: Date.now() - startedAtRef.current,
        hintsUsed: hintsUsedRef.current,
      },
      { onSuccess: (r) => { setResult(r); setPhase("answered"); } }
    );
  }

  function doReveal() {
    reveal.mutate(
      { itemId: card.itemId, latencyMs: Date.now() - startedAtRef.current },
      { onSuccess: (r) => { setRevealResult(r); setPhase("revealed"); } }
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

  function askHint() {
    setHintText(null);
    hint.mutate(
      {
        question: `Give me a hint for this recall card without revealing the answer: "${card.prompt}"`,
        style: "eli5",
      },
      { onSuccess: (r) => { setHintText(r.answer); hintsUsedRef.current += 1; } }
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
          "Before they answer or reveal it, guide recall without stating the answer. After the card is resolved, explain the concept clearly if asked.",
          `Card prompt: ${card.prompt}`,
          `Options: ${card.choices.map((choice) => `${choice.id}: ${choice.label}`).join(" | ")}`,
          `Card state: ${phase}.`,
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

  const reward = result?.reward ?? revealResult?.reward;
  const canAdvance = phase === "answered" || phase === "revealed";
  const dockPrimary = phase === "think"
    ? {
        label: "Reveal options",
        onClick: () => setPhase("choose" as const),
        icon: ArrowRightIcon,
      }
    : canAdvance
      ? {
          label: index + 1 >= total ? "See recap" : "Next card",
          onClick: nextCard,
          icon: ArrowRightIcon,
        }
      : {
          label: "Choose an answer to continue",
          onClick: () => {},
          disabled: true,
          icon: ArrowRightIcon,
        };

  return (
    <StudySurface
      bar={
        <SessionBar
          title="Flashcards"
          progress={{ current: index + 1, total, label: "card" }}
          onBack={onExit}
          backLabel="Choose another topic"
        />
      }
      dock={
        <ComposeDock
          primary={dockPrimary}
          onAsk={canAdvance ? askAboutCard : undefined}
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

        <TransitionPanel
          activeIndex={phaseIndex}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.22, ease: "easeOut" }}
          className="px-5 py-6"
        >
          {[
            // think — prompt alone, the recall beat
            <div key="think" className="space-y-5">
              <p className="text-lg font-medium leading-relaxed text-foreground">{card.prompt}</p>
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs text-muted-foreground">
                  Think of the answer first — then check yourself.
                </p>
              </div>
            </div>,
            // choose — AnswerableCard + Hint / Reveal actions
            <AnswerableCard
              key="choose"
              prompt={card.prompt}
              choices={card.choices}
              selectedId={selectedChoice}
              onSelect={answer}
              isPending={review.isPending || reveal.isPending}
              actions={
                <>
                  <Button variant="outline" size="sm" onClick={askHint} disabled={hint.isPending}>
                    {hint.isPending ? (
                      <Spinner className="size-3.5" />
                    ) : (
                      <BrainIcon size={15} className="text-muted-foreground" aria-hidden />
                    )}
                    {hint.isPending ? "Thinking…" : "Hint"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={doReveal} disabled={reveal.isPending}>
                    {reveal.isPending ? (
                      <Spinner className="size-3.5" />
                    ) : (
                      <EyeIcon size={15} className="text-muted-foreground" aria-hidden />
                    )}
                    {reveal.isPending ? "Committing…" : "Reveal · counts as missed"}
                  </Button>
                  {hintText ? (
                    <p className="w-full text-sm italic leading-relaxed text-muted-foreground">
                      {hintText}
                    </p>
                  ) : null}
                </>
              }
            />,
            // answered — graded result via AnswerableCard + Explain
            <AnswerableCard
              key="answered"
              prompt={card.prompt}
              choices={card.choices}
              selectedId={selectedChoice}
              onSelect={() => {}}
              result={
                result
                  ? {
                      correct: result.correct,
                      explanation: result.explanation,
                      mastery: result.mastery,
                    }
                  : null
              }
              meta={
                <>
                  <span>
                    next review in{" "}
                    {result?.dueInHours != null && result.dueInHours < 24
                      ? `${result.dueInHours}h`
                      : `${Math.round((result?.dueInHours ?? 0) / 24)}d`}
                  </span>
                  <span>box {result?.box}</span>
                  {result?.graduated ? <span className="text-brand-green">graduated ✓</span> : null}
                </>
              }
              actions={
                <>
                  <Button variant="outline" size="sm" onClick={askExplain} disabled={explain.isPending}>
                    {explain.isPending ? (
                      <Spinner className="size-3.5" />
                    ) : (
                      <SparklesIcon size={15} className="text-muted-foreground" aria-hidden />
                    )}
                    {explain.isPending ? "Thinking…" : "Explain more"}
                  </Button>
                  {explainText ? (
                    <p className="w-full text-sm italic leading-relaxed text-muted-foreground">
                      {explainText}
                    </p>
                  ) : null}
                </>
              }
            />,
            // revealed — committed lapse, answer shown (terminal for this card)
            <div key="revealed" className="space-y-4">
              <p className="text-sm font-semibold text-destructive">
                Revealed — counted as missed, so this card resurfaces sooner.
              </p>
              <div className="rounded-sm border border-brand-green/40 bg-brand-green/10 px-3 py-2.5">
                <p className="text-xs font-medium uppercase tracking-wide text-brand-green-foreground/70">
                  Answer
                </p>
                <p className="mt-0.5 text-sm font-semibold text-foreground">
                  {revealResult?.correctLabel ?? "—"}
                </p>
              </div>
              {revealResult?.explanation ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {revealResult.explanation}
                </p>
              ) : null}
              <div className="flex items-center gap-x-4 gap-y-1.5 border-t pt-2.5 font-mono text-xs text-muted-foreground">
                <span>
                  next review in{" "}
                  {revealResult && revealResult.dueInHours < 24
                    ? `${revealResult.dueInHours}h`
                    : `${Math.round((revealResult?.dueInHours ?? 0) / 24)}d`}
                </span>
                <span>box {revealResult?.box}</span>
                {revealResult?.mastery != null ? (
                  <span className="flex items-center gap-1.5">
                    mastery <MasteryBand band={bandFor(revealResult.mastery).band} />
                  </span>
                ) : null}
              </div>
            </div>,
          ]}
        </TransitionPanel>
        </div>

        {reward ? (
          <p className="text-right font-mono text-xs text-muted-foreground">
            {reward.streakDays}-day streak · {reward.xp} XP
          </p>
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
