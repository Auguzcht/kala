import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { TransitionPanel } from "@/components/motion/transition-panel";
import {
  useFlashcardDeck,
  useRevealFlashcard,
  useReviewFlashcard,
} from "@/features/flashcards/hooks/use-flashcards";
import { useTutorAsk } from "@/features/tutor";
import { useTwin } from "@/features/twin";
import { CornerBrackets, MasteryBand, bandFor } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type {
  FlashcardCard,
  FlashcardReviewResult,
  FlashcardRevealResult,
} from "@/features/flashcards/schema/flashcards.schema";

// Spaced-repetition recall quiz: prompt first (a think beat), then options,
// then Hint / Reveal / Explain as separate actions — matching the target
// design (Flashcards.dc.html). Grading is server-side; Reveal is a committed
// lapse, so a revealed card is terminal for this render (no follow-up review
// call — see routers/flashcards.py).

type Phase = "think" | "choose" | "answered" | "revealed";

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

export function FlashcardDeck({ courseId }: { courseId: string }) {
  const reduceMotion = useReducedMotion();
  const { data, isLoading, isError, refetch } = useFlashcardDeck(courseId, 10);
  const review = useReviewFlashcard(courseId);
  const reveal = useRevealFlashcard(courseId);
  const hint = useTutorAsk(courseId);
  const explain = useTutorAsk(courseId);
  const { data: twin } = useTwin(courseId);

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("think");
  const [deckDone, setDeckDone] = useState(false);
  const [result, setResult] = useState<FlashcardReviewResult | null>(null);
  const [revealResult, setRevealResult] = useState<FlashcardRevealResult | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const [explainText, setExplainText] = useState<string | null>(null);
  const hintsUsedRef = useRef(0);
  const startedAtRef = useRef(Date.now());

  useEffect(() => {
    setPhase("think");
    setDeckDone(false);
    setResult(null);
    setRevealResult(null);
    setHintText(null);
    setExplainText(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
  }, [index, data?.courseId]);

  if (isLoading)
    return (
      <LoadingPanel
        label="Building your deck — Kala is writing the first cards…"
        lines={4}
      />
    );
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
            ? "Nothing is due for review right now. Missed cards resurface sooner — come back later or practice now."
            : "Skills for this course haven't been mapped yet."
        }
        action={<Button variant="outline" onClick={() => refetch()}>Refresh deck</Button>}
      />
    );
  }

  const total = data.cards.length;

  if (deckDone) {
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <div>
            <p className="font-display text-3xl font-semibold leading-none text-foreground">
              {data.stats.due}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {data.stats.due === 1 ? "card" : "cards"} due for review now
            </p>
          </div>
          <div className="flex gap-4 pb-0.5 font-mono text-xs text-muted-foreground">
            <span>{data.stats.learning} learning</span>
            <span>{data.stats.mastered} mastered</span>
            <span>{data.stats.tracked} tracked</span>
          </div>
        </div>
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
          <div className="mt-4">
            <Button variant="orange" onClick={reloadDeck}>
              Reload deck
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const card: FlashcardCard = data.cards[index];
  const band = twin?.skills.find((s) => s.skillId === card.skillId)?.band;

  function answer(choiceId: string) {
    setPhase("choose");
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
      // Deck complete — refresh so the recap shows the real due count.
      setDeckDone(true);
      refetch();
      return;
    }
    setIndex((i) => i + 1);
  }

  function reloadDeck() {
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

  const reward = result?.reward ?? revealResult?.reward;

  const phaseIndex =
    phase === "think" ? 0 : phase === "choose" ? 1 : phase === "answered" ? 2 : 3;

  return (
    <div className="space-y-5">
      {/* The one number that drives the next action: due for review. */}
      <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
        <div>
          <p className="font-display text-3xl font-semibold leading-none text-foreground">
            {data.stats.due}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {data.stats.due === 1 ? "card" : "cards"} due for review now
          </p>
        </div>
        <div className="flex gap-4 pb-0.5 font-mono text-xs text-muted-foreground">
          <span>{data.stats.learning} learning</span>
          <span>{data.stats.mastered} mastered</span>
          <span>{data.stats.tracked} tracked</span>
        </div>
      </div>

      <div className="relative border bg-card">
        <CornerBrackets />
        <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="truncate text-sm font-semibold text-foreground">
              {card.skillName ?? "Card"}
            </span>
            {band ? <MasteryBand band={band} /> : null}
            <StateBadge state={card.state} />
          </div>
          <span className="shrink-0 font-mono text-xs text-muted-foreground">
            {index + 1}/{total} · box {card.box}
          </span>
        </div>

        <TransitionPanel
          activeIndex={phaseIndex}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.22, ease: "easeOut" }}
          className="px-5 py-6"
        >
          {[
            // think — prompt alone, the recall beat
            <div key="think" className="space-y-5">
              <p className="text-lg font-medium leading-relaxed text-foreground">
                {card.prompt}
              </p>
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs text-muted-foreground">
                  Think of the answer first — then check yourself.
                </p>
                <Button variant="orange" onClick={() => setPhase("choose")}>
                  Reveal options
                </Button>
              </div>
            </div>,
            // choose — options + Hint / Reveal actions
            <div key="choose" className="space-y-5">
              <p className="text-lg font-medium leading-relaxed text-foreground">
                {card.prompt}
              </p>
              <div className="space-y-4">
                <div className="flex flex-col gap-2">
                  {card.choices.map((c) => (
                    <Button
                      key={c.id}
                      variant="outline"
                      disabled={review.isPending || reveal.isPending}
                      onClick={() => answer(c.id)}
                      className="h-auto justify-start whitespace-normal text-left"
                    >
                      {c.label}
                    </Button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="outline" size="sm" onClick={askHint} disabled={hint.isPending}>
                    {hint.isPending ? "Thinking…" : "Hint"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={doReveal} disabled={reveal.isPending}>
                    {reveal.isPending ? "Committing…" : "Reveal answer · counts as missed"}
                  </Button>
                  {hintText ? (
                    <p className="w-full text-sm italic leading-relaxed text-muted-foreground">
                      {hintText}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>,
            // answered — graded result
            <div key="answered" className="space-y-4">
              <p
                className={cn(
                  "text-sm font-semibold",
                  result?.correct ? "text-brand-green" : "text-destructive"
                )}
              >
                {result?.correct ? "Correct." : "Not quite."}
              </p>
              {result?.explanation ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {result.explanation}
                </p>
              ) : null}
              <ResultMeta
                correct={result?.correct ?? false}
                dueInHours={result?.dueInHours ?? 0}
                box={result?.box ?? 0}
                mastery={result?.mastery ?? null}
                graduated={result?.graduated}
              />
              {explainText ? (
                <p className="rounded-sm border bg-muted/50 p-3 text-sm leading-relaxed text-muted-foreground">
                  {explainText}
                </p>
              ) : null}
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button variant="outline" size="sm" onClick={askExplain} disabled={explain.isPending}>
                  {explain.isPending ? "Thinking…" : "Explain more"}
                </Button>
                <Button variant="orange" onClick={nextCard}>
                  {index + 1 >= total ? "See recap" : "Next card"}
                </Button>
              </div>
            </div>,
            // revealed — committed lapse, answer shown
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
              <ResultMeta
                correct={false}
                dueInHours={revealResult?.dueInHours ?? 0}
                box={revealResult?.box ?? 0}
                mastery={revealResult?.mastery ?? null}
              />
              <Button variant="orange" onClick={nextCard}>
                {index + 1 >= total ? "See recap" : "Next card"}
              </Button>
            </div>,
          ]}
        </TransitionPanel>
      </div>

      {reward ? (
        <p className="text-right font-mono text-xs text-muted-foreground">
          {reward.streakDays}-day streak · {reward.xp} XP
        </p>
      ) : null}
    </div>
  );
}

function ResultMeta({
  correct,
  dueInHours,
  box,
  mastery,
  graduated,
}: {
  correct: boolean;
  dueInHours: number;
  box: number;
  mastery: number | null;
  graduated?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-3 font-mono text-xs text-muted-foreground">
      <span>
        next review in {dueInHours < 24 ? `${dueInHours}h` : `${Math.round(dueInHours / 24)}d`}
      </span>
      <span>box {box}</span>
      {mastery != null ? (
        <span className="inline-flex items-center gap-1.5">
          mastery <MasteryBand band={bandFor(mastery).band} />
        </span>
      ) : null}
      {graduated ? <span className="text-brand-green">graduated ✓</span> : null}
      <span>{correct ? "earned" : "lapsed"}</span>
    </div>
  );
}
