import { useEffect, useRef, type ReactNode } from "react";
import { CheckIcon } from "@/components/ui/check";
import type { CheckIconHandle } from "@/components/ui/check";
import { XIcon } from "@/components/ui/x";
import type { XIconHandle } from "@/components/ui/x";
import { MasteryBand, bandFor } from "@/components/kala";
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
} | null;

export function AnswerableCard({
  prompt,
  choices,
  selectedId,
  onSelect,
  result,
  isPending = false,
  actions,
  meta,
}: {
  prompt: string;
  choices: { id: string; label: string }[];
  selectedId: string | null;
  onSelect: (choiceId: string) => void;
  result?: AnswerableResult;
  isPending?: boolean;
  actions?: ReactNode;
  meta?: ReactNode;
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

  return (
    <div className="space-y-4">
      <p className="text-lg font-medium leading-relaxed text-foreground">{prompt}</p>

      <div className="flex flex-col gap-2">
        {choices.map((c) => (
          <Button
            key={c.id}
            variant={selectedId === c.id ? "orange" : "outline"}
            disabled={!!result || isPending}
            onClick={() => onSelect(c.id)}
            className="h-auto justify-start whitespace-normal text-left transition-colors hover:border-brand-orange/40 hover:bg-accent/40"
          >
            {isPending && selectedId === c.id ? <Spinner className="size-3.5" /> : null}
            {c.label}
          </Button>
        ))}
      </div>

      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}

      {result ? (
        <div className="space-y-3">
          <div className="flex items-start gap-2.5">
            {result.correct ? (
              <CheckIcon ref={checkRef} size={18} className="mt-0.5 shrink-0 text-brand-green" aria-hidden />
            ) : (
              <XIcon ref={xRef} size={18} className="mt-0.5 shrink-0 text-destructive" aria-hidden />
            )}
            <div className="space-y-1">
              <p
                className={cn(
                  "text-sm font-semibold",
                  result.correct ? "text-brand-green" : "text-destructive"
                )}
              >
                {result.correct ? "Correct." : "Not quite."}
              </p>
              {result.explanation ? (
                <p className="text-sm leading-relaxed text-muted-foreground">{result.explanation}</p>
              ) : null}
            </div>
          </div>

          {result.mastery != null || meta ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t pt-2.5 font-mono text-xs text-muted-foreground">
              {result.mastery != null ? (
                <span className="flex items-center gap-1.5">
                  mastery <MasteryBand band={bandFor(result.mastery).band} />
                </span>
              ) : null}
              {meta}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
