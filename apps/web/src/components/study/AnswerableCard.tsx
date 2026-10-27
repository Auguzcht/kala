import { useEffect, useRef, useState, type ReactNode } from "react";
import { CheckIcon } from "@/components/ui/check";
import type { CheckIconHandle } from "@/components/ui/check";
import { XIcon } from "@/components/ui/x";
import type { XIconHandle } from "@/components/ui/x";
import { MarkdownText } from "@/components/study/MarkdownText";
import { CornerBrackets, MasteryBand, bandFor } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

// The reusable question/content card — one implementation for every surface
// that shows a prompt with choices and grades them: Practice, Flashcards
// (deck + reveal), Lessons' comprehension checks, and (structurally) the
// diagnostic. Merges the best bits that lived in four bespoke copies:
// PracticePanel's hover/selected states and its disabled-during-pending fix
// (a real double-submit window), FlashcardDeck's graded-result presentation.
//
// `actions` is the surface-specific slot: Flashcards passes Hint / Reveal /
// Explain there, Lessons passes a Hint, Practice passes nothing.
// `meta` is the surface-specific graded-result detail (next-due, box,
// graduation…) rendered under the explanation.
// `mastery` in `result` renders the live mastery band.

export type AnswerableResult = {
  correct: boolean;
  explanation: string;
  mastery?: number | null;
  correctChoiceId?: string | null;
} | null;

export function AnswerableCard({
  prompt,
  choices,
  selectedId,
  onSelect,
  result,
  isPending = false,
  pendingFeedback = true,
  actions,
  meta,
  framed = true,
  id,
  eyebrow,
  choicesAnchorId,
  resultAnchorId,
  firstChoiceId = "tour-first-choice",
}: {
  prompt: string;
  choices: { id: string; label: string }[];
  selectedId: string | null;
  onSelect: (choiceId: string) => void;
  result?: AnswerableResult;
  isPending?: boolean;
  /** Bulk submission locks choices but shows feedback in its submit control. */
  pendingFeedback?: boolean;
  actions?: ReactNode;
  meta?: ReactNode;
  /** Render the shared instrument-panel frame around this question. */
  framed?: boolean;
  /** Optional surface or tour anchor id for the card frame. */
  id?: string;
  /** Small label shown above the prompt inside the frame. */
  eyebrow?: string;
  /** Tour anchor for the choices block. */
  choicesAnchorId?: string;
  /** Tour anchor for the graded-result block. */
  resultAnchorId?: string;
  /** id for the first choice button, defaults to "tour-first-choice" (what
   * Lessons' and Practice's tour steps click through). Every surface but
   * one shows a single AnswerableCard at a time, so the default is safe.
   * Diagnostic renders N of these on one page simultaneously — pass null
   * there, or every question's first choice would share the same id. */
  firstChoiceId?: string | null;
}) {
  // One-shot animation on the graded result landing (motion encodes state
  // change): the check/x draw once when the result appears, never on hover
  // churn and never looping. Refs stay null until a result actually exists.
  const checkRef = useRef<CheckIconHandle | null>(null);
  const xRef = useRef<XIconHandle | null>(null);
  useEffect(() => {
    if (!result) return;
    (result.correct ? checkRef : xRef).current?.startAnimation();
  }, [result]);

  // Grading is a DB lookup (the answer key is already stored server-side),
  // not a model call — the round trip is normally well under 200ms. Showing
  // a spinner the INSTANT the request fires (isPending flips true on the
  // same tick as the click) makes a fast, ordinary click read as "loading
  // the answer," which is exactly the wrong impression for something this
  // quick. Delay the spinner: if the request resolves before the delay
  // elapses (the common case), no spinner ever renders at all. A genuinely
  // slow response (network hiccup, cold start) still gets one, just not
  // for the normal fast path. Buttons stay disabled immediately either
  // way — that's what actually prevents a double-submit, not the spinner.
  const [showSpinner, setShowSpinner] = useState(false);
  useEffect(() => {
    if (!isPending || !pendingFeedback) {
      setShowSpinner(false);
      return;
    }
    const timer = setTimeout(() => setShowSpinner(true), 200);
    return () => clearTimeout(timer);
  }, [isPending, pendingFeedback]);

  return (
    <div
      id={id}
      className={framed ? "relative border bg-card px-5 py-6 sm:px-6" : undefined}
    >
      {framed ? <CornerBrackets /> : null}
      <div className="space-y-4">
      {eyebrow ? (
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{eyebrow}</p>
      ) : null}
      <p className="text-lg font-medium leading-relaxed text-foreground">{prompt}</p>

      <div id={choicesAnchorId} className="flex flex-col gap-2">
        {choices.map((c, ci) => (
          (() => {
            const isCorrectChoice = Boolean(result && (
              result.correctChoiceId
                ? c.id === result.correctChoiceId
                : result.correct && c.id === selectedId
            ));
            const isWrongSelection = Boolean(result && selectedId === c.id && !isCorrectChoice);
            return (
              <Button
                key={c.id}
                id={ci === 0 ? (firstChoiceId ?? undefined) : undefined}
                variant={isCorrectChoice ? "outline" : selectedId === c.id ? "orange" : "outline"}
                disabled={!!result || isPending}
                aria-pressed={selectedId === c.id}
                onClick={() => onSelect(c.id)}
                className={cn(
                  "h-auto justify-start whitespace-normal text-left transition-colors",
                  !result && selectedId !== c.id && "hover:border-brand-orange/40 hover:bg-accent/40",
                  isCorrectChoice && "border-brand-green bg-brand-green/10 text-foreground",
                  isWrongSelection && "border-destructive bg-destructive/10 text-foreground",
                )}
              >
                {showSpinner && selectedId === c.id ? <Spinner className="size-3.5" /> : null}
                {c.label}
                {isCorrectChoice ? <span className="ml-auto shrink-0 text-xs font-semibold text-brand-green">Correct</span> : null}
              </Button>
            );
          })()
        ))}
      </div>

      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}

      {result ? (
        <div id={resultAnchorId} className="space-y-3 border-t pt-4">
          <div className="flex items-start gap-2.5">
            {result.correct ? (
              <CheckIcon ref={checkRef} size={18} className="mt-0.5 shrink-0 text-brand-green" aria-hidden />
            ) : (
              <XIcon ref={xRef} size={18} className="mt-0.5 shrink-0 text-destructive" aria-hidden />
            )}
            <div className="min-w-0 space-y-1">
              {/* Verdict and mastery share one line: the band is what the
                  answer *did* to the student's twin, which belongs with the
                  correct/incorrect verdict it resulted from — not stranded
                  under the explanation behind a rule, where it read as an
                  unrelated statistic and got scanned last. */}
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                <p
                  className={cn(
                    "text-sm font-semibold",
                    result.correct ? "text-brand-green" : "text-destructive"
                  )}
                >
                  {result.correct ? "Correct." : "Not quite."}
                </p>
                {result.mastery != null ? (
                  <span className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                    mastery <MasteryBand band={bandFor(result.mastery).band} />
                  </span>
                ) : null}
              </div>
              {result.explanation ? (
                <div className="text-sm text-muted-foreground">
                  {/* The explanation is model-generated and may carry
                      markdown (lists, bold, code) — render it, don't show
                      the syntax. Not animated: this is reference text that
                      should already be there when the result appears, unlike
                      a reply being written out to the student. */}
                  <MarkdownText
                    className="text-sm leading-relaxed text-muted-foreground"
                    animate={false}
                  >
                    {result.explanation}
                  </MarkdownText>
                </div>
              ) : null}
            </div>
          </div>

          {/* Surface-specific detail only (next-due, box, graduation…). */}
          {meta ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-xs text-muted-foreground">
              {meta}
            </div>
          ) : null}
        </div>
      ) : null}
      </div>
    </div>
  );
}
