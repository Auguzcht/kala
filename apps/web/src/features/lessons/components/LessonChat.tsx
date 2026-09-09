import { useState, useRef, useEffect } from "react";
import { BrainIcon } from "@/components/ui/brain";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { StudyStream } from "@/components/study/StudyStream";
import { TeachingBlock } from "@/components/study/TeachingBlock";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { CornerBrackets } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLesson, useSubmitStepCheck } from "@/features/lessons/hooks/use-lessons";
import { useTutorAsk } from "@/features/tutor";
import { cn } from "@/lib/utils";
import type { LessonCheckResult } from "@/features/lessons/schema/lessons.schema";

// Guided lesson as a guided stream (Stage 1 of the AI-overhaul plan, see
// docs/AI_OVERHAUL_TODO.md): Kala teaches step by step in a continuous
// thread, and each step ends with a suggested-reply chip ("I understand —
// continue"). Continuing reveals the step's comprehension check as the
// NEXT block in the same stream — this used to be a Dialog that covered
// the thread; Gizmo's own lesson flow (the reference point for this
// rework) never does that, the check is just the next thing you scroll to.
// Only a correct check advances the thread — the gate stays server-side
// (advance: true), nothing about that changed.

export function LessonChat({ courseId, skillId }: { courseId: string; skillId: string }) {
  const { data, isLoading, isError, refetch } = useLesson(courseId, skillId);
  const submit = useSubmitStepCheck(courseId);
  const hint = useTutorAsk(courseId);

  const [stepIndex, setStepIndex] = useState(0);
  const [checkOpen, setCheckOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<LessonCheckResult | null>(null);
  const [hintText, setHintText] = useState<string | null>(null);
  const hintsUsedRef = useRef(0);
  const startedAtRef = useRef(Date.now());

  // Reset on a genuinely new lesson load (a different skillId resolving),
  // not on every step — per-step state resets when that step's check
  // actually opens (openCheck below), same boundary the original modal
  // version used.
  useEffect(() => {
    setStepIndex(0);
    setCheckOpen(false);
    setSelected(null);
    setResult(null);
    setHintText(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
  }, [data?.lessonId]);

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

  function openCheck() {
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
    setCheckOpen(true);
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

  function advanceStep() {
    setCheckOpen(false);
    setStepIndex((i) => i + 1);
  }

  function retry() {
    setSelected(null);
    setResult(null);
    startedAtRef.current = Date.now();
  }

  const assistantBubble = "mr-auto flex max-w-[88%] items-start gap-2.5";

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

        <StudyStream>
          {/* Completed steps: teaching + outcome */}
          {data.steps.slice(0, done ? total : stepIndex).map((s) => (
            <div key={s.id} className="space-y-3">
              <TeachingBlock step={s} />
              <div className={cn("flex items-center gap-2", assistantBubble)}>
                <span className="rounded-sm border border-brand-green/40 bg-brand-green/10 px-2.5 py-1 text-xs font-semibold text-brand-green">
                  Step complete ✓
                </span>
              </div>
            </div>
          ))}

          {/* Current step: teaching, then continue OR the inline check */}
          {current ? (
            <div className="space-y-3">
              <TeachingBlock step={current} id="tour-lesson-explain" />

              {!checkOpen ? (
                <div className={cn("flex flex-wrap items-center gap-2", assistantBubble)}>
                  <p className="text-xs text-muted-foreground">When you're ready, continue to the check.</p>
                  <button
                    type="button"
                    id="tour-lesson-continue"
                    onClick={openCheck}
                    className="inline-flex items-center gap-1.5 rounded-full border border-brand-orange/50 bg-brand-orange/10 px-3.5 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-brand-orange/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <GraduationCapIcon size={15} className="text-brand-orange" aria-hidden />
                    I understand — continue
                  </button>
                </div>
              ) : null}

              {checkOpen && current.check ? (
                <div id="tour-lesson-check" className="mr-auto max-w-[92%] space-y-4">
                  <div className="rounded-md border bg-card p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Check yourself
                    </p>
                    <AnswerableCard
                      prompt={current.check.prompt}
                      choices={current.check.choices}
                      selectedId={selected}
                      onSelect={choose}
                      isPending={submit.isPending}
                      resultAnchorId="tour-lesson-check-feedback"
                      result={
                        result
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
                  </div>

                  {result?.advance ? (
                    <div className="flex justify-end">
                      <Button variant="orange" onClick={advanceStep}>
                        {stepIndex + 1 >= total ? "Finish lesson" : "Next step"}
                      </Button>
                    </div>
                  ) : result ? (
                    <div className="flex justify-end">
                      <Button variant="outline" onClick={retry}>
                        Try again
                      </Button>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {/* Done */}
          {done ? (
            <div className={cn(assistantBubble)}>
              <img src="/Kala-Logo.png" alt="Kala" className="mt-0.5 size-7 shrink-0 object-contain" />
              <div className="min-w-0 space-y-3 rounded-md border bg-card px-4 py-3.5 text-sm leading-relaxed text-foreground">
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
        </StudyStream>
      </div>
    </StudySessionShell>
  );
}
