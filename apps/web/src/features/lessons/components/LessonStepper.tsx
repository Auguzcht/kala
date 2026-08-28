import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import { TransitionPanel } from "@/components/motion/transition-panel";
import { useLesson, useSubmitStepCheck } from "@/features/lessons/hooks/use-lessons";
import { CornerBrackets, MasteryBand, bandFor } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type {
  LessonCheckResult,
  LessonStep,
} from "@/features/lessons/schema/lessons.schema";

// Guided lesson stepper: read -> understand -> apply, one step at a time.
// Each step teaches (summary, detail points, misconception, takeaway) then
// gates progress on a server-graded comprehension check. The step advances
// ONLY when the API says so (advance: true) — the client never skips.
// Step bodies run through TransitionPanel so advancing is a real state
// change with motion, not a hard content swap.

export function LessonStepper({
  courseId,
  skillId,
}: {
  courseId: string;
  skillId: string;
}) {
  const reduceMotion = useReducedMotion();
  const { data, isLoading, isError, refetch } = useLesson(courseId, skillId);
  const submit = useSubmitStepCheck(courseId);

  const [stepIndex, setStepIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<LessonCheckResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [done, setDone] = useState(false);

  useEffect(() => {
    setStepIndex(0);
    setSelected(null);
    setResult(null);
    setStartedAt(Date.now());
    setDone(false);
  }, [data?.lessonId]);

  if (isLoading || data?.status === "generating")
    return (
      <LoadingPanel
        label="Kala is writing your lesson — first pass takes a moment…"
        lines={5}
        className="max-w-2xl"
      />
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

  const lastStep = stepIndex >= data.steps.length - 1;

  function choose(step: LessonStep, choiceId: string) {
    if (!step.check || result) return;
    setSelected(choiceId);
    submit.mutate(
      {
        stepId: step.id,
        itemId: step.check.itemId,
        choiceId,
        latencyMs: Date.now() - startedAt,
      },
      { onSuccess: (r) => setResult(r) }
    );
  }

  function advance() {
    if (lastStep) {
      setDone(true);
    } else {
      setStepIndex((i) => i + 1);
      setSelected(null);
      setResult(null);
      setStartedAt(Date.now());
    }
  }

  return (
    <div className="space-y-5">
      {/* Stepper rail */}
      <ol className="flex flex-wrap items-center gap-2" aria-label="Lesson steps">
        {data.steps.map((s, i) => (
          <li
            key={s.id}
            className={cn(
              "flex items-center gap-1.5 rounded-sm border px-2 py-1 text-xs font-medium",
              i === stepIndex
                ? "border-brand-orange/60 bg-brand-orange/10 text-foreground"
                : i < stepIndex
                  ? "border-border bg-muted text-muted-foreground"
                  : "border-border text-muted-foreground/60"
            )}
          >
            <span
              className={cn(
                "grid size-4 place-items-center rounded-[2px] font-mono text-[10px]",
                i < stepIndex ? "bg-brand-green text-white" : "bg-muted text-muted-foreground"
              )}
            >
              {i < stepIndex ? "✓" : i + 1}
            </span>
            <span className="hidden sm:inline">{s.summary}</span>
            <span className="sm:hidden">Step {i + 1}</span>
          </li>
        ))}
      </ol>

      {done ? (
        <div className="relative border bg-card p-6">
          <CornerBrackets />
          <p className="text-xs font-medium uppercase tracking-[0.06em] text-brand-slate">
            Lesson complete
          </p>
          <p className="mt-1.5 font-display text-lg font-semibold text-foreground">
            {data.title}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            You worked through all {data.steps.length} steps. The check answers fed your twin —
            keep the concepts fresh with spaced review.
          </p>
          <div className="mt-4 flex gap-3">
            <Button variant="orange" onClick={() => refetch()}>
              Start again
            </Button>
          </div>
        </div>
      ) : (
        <div className="relative border bg-card">
          <CornerBrackets />
          <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <span className="truncate text-sm font-semibold text-foreground">
                {data.title}
              </span>
              {data.steps[stepIndex]?.bloomLevel ? (
                <span className="rounded-sm border bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold text-muted-foreground">
                  {data.steps[stepIndex].bloomLevel}
                </span>
              ) : null}
            </div>
            <span className="shrink-0 font-mono text-xs text-muted-foreground">
              Step {stepIndex + 1}/{data.steps.length}
            </span>
          </div>

          <TransitionPanel
            activeIndex={stepIndex}
            transition={reduceMotion ? { duration: 0 } : { duration: 0.25, ease: "easeOut" }}
            className="px-5 py-6"
          >
            {data.steps.map((s) => (
              <div key={s.id} className="space-y-4">
                <p className="text-lg font-medium leading-relaxed text-foreground">{s.summary}</p>

                {s.detailPoints.length > 0 ? (
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    {s.detailPoints.map((d, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="mt-1.5 size-1 shrink-0 rounded-full bg-brand-slate/50" />
                        <span className="leading-relaxed">{d}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}

                {s.misconception ? (
                  <div className="border-l-2 border-destructive/60 pl-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-destructive">
                      Common misconception
                    </p>
                    <p className="mt-0.5 text-sm text-muted-foreground">{s.misconception}</p>
                  </div>
                ) : null}

                {s.keyTakeaway ? (
                  <div className="border-l-2 border-brand-gold pl-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-brand-gold-foreground/70">
                      Key takeaway
                    </p>
                    <p className="mt-0.5 text-sm font-medium text-foreground">{s.keyTakeaway}</p>
                  </div>
                ) : null}

                {s.check ? (
                  <div className="space-y-3 border-t pt-4">
                    <p className="text-sm font-semibold text-foreground">Check yourself</p>
                    <p className="text-sm text-muted-foreground">{s.check.prompt}</p>
                    <div className="flex flex-col gap-2">
                      {s.check.choices.map((c) => (
                        <Button
                          key={c.id}
                          variant={selected === c.id ? "orange" : "outline"}
                          disabled={!!result || submit.isPending}
                          onClick={() => choose(s, c.id)}
                          className="h-auto justify-start whitespace-normal text-left"
                        >
                          {c.label}
                        </Button>
                      ))}
                    </div>

                    {result ? (
                      <div className="space-y-3">
                        <p
                          className={cn(
                            "text-sm font-semibold",
                            result.correct ? "text-brand-green" : "text-destructive"
                          )}
                        >
                          {result.correct ? "Correct — that step is solid." : "Not quite."}
                        </p>
                        {result.explanation ? (
                          <p className="text-sm leading-relaxed text-muted-foreground">
                            {result.explanation}
                          </p>
                        ) : null}
                        {result.mastery != null ? (
                          <p className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                            mastery <MasteryBand band={bandFor(result.mastery).band} />
                          </p>
                        ) : null}
                        {result.advance ? (
                          <Button variant="orange" onClick={advance}>
                            {lastStep ? "Finish lesson" : "Next step"}
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            onClick={() => {
                              setSelected(null);
                              setResult(null);
                              setStartedAt(Date.now());
                            }}
                          >
                            Try again
                          </Button>
                        )}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="border-t pt-4">
                    <Button variant="orange" onClick={advance}>
                      {lastStep ? "Finish lesson" : "Next step"}
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </TransitionPanel>
        </div>
      )}
    </div>
  );
}
