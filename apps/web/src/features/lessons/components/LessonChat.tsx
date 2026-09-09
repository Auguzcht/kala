import { useEffect, useRef, useState } from "react";
import { BrainIcon } from "@/components/ui/brain";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CornerBrackets } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLesson, useSubmitStepCheck } from "@/features/lessons/hooks/use-lessons";
import { useTutorAsk } from "@/features/tutor";
import { cn } from "@/lib/utils";
import type { LessonCheckResult } from "@/features/lessons/schema/lessons.schema";

// Guided lesson as a guided CHAT — Kala teaches step by step in a thread,
// the way the tutor does, and each step ends with a suggested-reply chip
// ("I understand — continue"). Continuing opens the step's comprehension
// check as a MODAL flashcard (answerable card, grounded to the same lesson
// context, Hint via the tutor), and only a correct check advances the
// thread — the gate stays server-side (advance: true).

export function LessonChat({ courseId, skillId }: { courseId: string; skillId: string }) {
  const { data, isLoading, isError, refetch } = useLesson(courseId, skillId);
  const submit = useSubmitStepCheck(courseId);
  const hint = useTutorAsk(courseId);

  const [stepIndex, setStepIndex] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<LessonCheckResult | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const hintsUsedRef = useRef(0);
  const startedAtRef = useRef(Date.now());
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setStepIndex(0);
    setModalOpen(false);
    setSelected(null);
    setResult(null);
    setHintText(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
  }, [data?.lessonId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [stepIndex, data?.lessonId, modalOpen]);

  if (isLoading || data?.status === "generating")
    return (
      <div id="tour-lesson-generating" className="w-full">
        <LoadingPanel label="Kala is writing your lesson — first pass takes a moment…" lines={5} />
      </div>
    );
  if (isError)
    return (
      <EmptyState
        title="We could not load this lesson"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (!data || data.steps.length === 0)
    return (
      <EmptyState
        title="No lesson here yet"
        description="This skill doesn't have a lesson yet. Come back after course content is ingested."
      />
    );

  const total = data.steps.length;
  const done = stepIndex >= total;
  const current = done ? null : data.steps[stepIndex];

  function continueToCheck() {
    if (!current?.check) {
      // Pure-explanation step: nothing to grade, advance straight on.
      setStepIndex((i) => i + 1);
      return;
    }
    setSelected(null);
    setResult(null);
    setHintText(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
    setModalOpen(true);
  }

  function choose(choiceId: string) {
    if (!current?.check || result) return;
    setSelected(choiceId);
    submit.mutate(
      {
        stepId: current.id,
        itemId: current.check.itemId,
        choiceId,
        latencyMs: Date.now() - startedAtRef.current,
        hintsUsed: hintsUsedRef.current,
      },
      { onSuccess: (r) => setResult(r) }
    );
  }

  function askHint() {
    if (!current?.check) return;
    setHintText(null);
    hint.mutate(
      {
        question: `Give me a hint for this comprehension check without revealing the answer: "${current.check.prompt}"`,
        style: "eli5",
      },
      { onSuccess: (r) => { setHintText(r.answer); hintsUsedRef.current += 1; } }
    );
  }

  function closeModalAndAdvance() {
    setModalOpen(false);
    setStepIndex((i) => i + 1);
  }

  function retry() {
    setSelected(null);
    setResult(null);
    startedAtRef.current = Date.now();
  }

  const assistantBubble = "mr-auto flex max-w-[88%] items-start gap-2.5";
  const assistantCard =
    "min-w-0 space-y-3 rounded-md border bg-card px-4 py-3.5 text-sm leading-relaxed text-foreground";

  return (
    <StudySessionShell
      progress={done ? { current: total, total, label: "step" } : { current: stepIndex + 1, total, label: "step" }}
    >
      <div className="relative border bg-card">
        <CornerBrackets />
        <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
          <span className="truncate text-sm font-semibold text-foreground">{data.title}</span>
          <span className="shrink-0 font-mono text-xs text-muted-foreground">
            {done ? total : stepIndex + 1}/{total} steps
          </span>
        </div>

        <div ref={scrollRef} className="max-h-[62vh] space-y-5 overflow-y-auto px-5 py-6">
          {/* Completed steps: teaching + outcome */}
          {data.steps.slice(0, done ? total : stepIndex).map((s) => (
            <div key={s.id} className="space-y-3">
              <TeachingMessage step={s} bubble={assistantBubble} card={assistantCard} />
              <div className={cn("flex items-center gap-2", assistantBubble)}>
                <span className="rounded-sm border border-brand-green/40 bg-brand-green/10 px-2.5 py-1 text-xs font-semibold text-brand-green">
                  Step complete ✓
                </span>
              </div>
            </div>
          ))}

          {/* Current step teaching + continue chip */}
          {current ? (
            <>
              <TeachingMessage step={current} bubble={assistantBubble} card={assistantCard} id="tour-lesson-explain" />
              <div className={cn("flex flex-wrap items-center gap-2", assistantBubble)}>
                <p className="text-xs text-muted-foreground">When you're ready, continue to the check.</p>
                <button
                  type="button"
                  id="tour-lesson-continue"
                  onClick={continueToCheck}
                  className="inline-flex items-center gap-1.5 rounded-full border border-brand-orange/50 bg-brand-orange/10 px-3.5 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-brand-orange/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <GraduationCapIcon size={15} className="text-brand-orange" aria-hidden />
                  I understand — continue
                </button>
              </div>
            </>
          ) : null}

          {/* Done */}
          {done ? (
            <div className={cn(assistantBubble)}>
              <img src="/Kala-Logo.png" alt="Kala" className="mt-0.5 size-7 shrink-0 object-contain" />
              <div className={cn(assistantCard)}>
                <p className="font-medium">Lesson complete — nice work.</p>
                <p className="text-muted-foreground">
                  You worked through all {total} steps. The check answers fed your twin — keep the
                  concepts fresh with spaced review.
                </p>
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  Start again
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* The comprehension check as a modal flashcard, grounded to this lesson */}
      <Dialog open={modalOpen} onOpenChange={(open) => { if (!submit.isPending) setModalOpen(open); }}>
        <DialogContent id="tour-lesson-check" className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base">Check yourself</DialogTitle>
            <DialogDescription>
              One question on what Kala just taught. Correct answers advance the lesson.
            </DialogDescription>
          </DialogHeader>

          {current?.check ? (
            <AnswerableCard
              prompt={current.check.prompt}
              choices={current.check.choices}
              selectedId={selected}
              onSelect={choose}
              isPending={submit.isPending}
              resultAnchorId="tour-lesson-check-feedback"
              result={result
                  ? {
                      correct: result.correct,
                      explanation: result.explanation,
                      mastery: result.mastery,
                    }
                  : null
              }
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
                  {hintText ? (
                    <p className="w-full text-sm italic leading-relaxed text-muted-foreground">
                      {hintText}
                    </p>
                  ) : null}
                </>
              }
            />
          ) : null}

          <div className="flex justify-end gap-2 border-t pt-4">
            {result?.advance ? (
              <Button variant="orange" onClick={closeModalAndAdvance}>
                {stepIndex + 1 >= total ? "Finish lesson" : "Next step"}
              </Button>
            ) : result ? (
              <Button variant="outline" onClick={retry}>
                Try again
              </Button>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
    </StudySessionShell>
  );
}

// One step's teaching content rendered as a structured assistant message.
function TeachingMessage({
  step,
  bubble,
  card,
  id,
}: {
  step: { summary: string; detailPoints: string[]; misconception: string | null; keyTakeaway: string | null; bloomLevel: string | null };
  bubble: string;
  card: string;
  id?: string;
}) {
  return (
    <div className={cn(bubble)}>
      <img src="/Kala-Logo.png" alt="Kala" className="mt-0.5 size-7 shrink-0 object-contain" />
      <div id={id} className={cn(card)}>
        <div className="flex items-center gap-2">
          <p className="font-medium text-foreground">{step.summary}</p>
          {step.bloomLevel ? (
            <span className="rounded-sm border bg-muted px-1.5 py-0.5 text-[10px] font-semibold capitalize text-muted-foreground">
              {step.bloomLevel}
            </span>
          ) : null}
        </div>

        {step.detailPoints.length > 0 ? (
          <ul className="space-y-1.5 text-muted-foreground">
            {step.detailPoints.map((d, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-brand-slate/50" />
                <span className="leading-relaxed">{d}</span>
              </li>
            ))}
          </ul>
        ) : null}

        {step.misconception ? (
          <div className="border-l-2 border-destructive/60 pl-3">
            <p className="text-xs font-medium uppercase tracking-wide text-destructive">
              Common misconception
            </p>
            <p className="mt-0.5 text-muted-foreground">{step.misconception}</p>
          </div>
        ) : null}

        {step.keyTakeaway ? (
          <div className="border-l-2 border-brand-gold pl-3">
            <p className="text-xs font-medium uppercase tracking-wide text-brand-gold-foreground/70">
              Key takeaway
            </p>
            <p className="mt-0.5 font-medium text-foreground">{step.keyTakeaway}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
