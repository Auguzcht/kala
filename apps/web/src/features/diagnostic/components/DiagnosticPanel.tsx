import { useMemo, useState } from "react";
import { useDiagnostic, useSubmitDiagnostic } from "@/features/diagnostic/hooks/use-diagnostic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { MasteryDelta } from "@/components/kala";
import type { Answer, AnswerResult } from "@/features/diagnostic/schema/diagnostic.schema";

// Worked-example component. Shows the feature wiring: query hook -> UI ->
// mutation hook. One RAG-grounded question per skill, self-paced, graded
// server-side (the client only ever picks a choice, never a correctness
// claim).
export function DiagnosticPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError } = useDiagnostic(courseId);
  const submit = useSubmitDiagnostic(courseId);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [startedAt] = useState(() => Date.now());
  const [resultsByItem, setResultsByItem] = useState<Record<string, AnswerResult>>({});

  // Memoized on the actual masteryDelta reference (stable from React Query
  // until a real refetch), not recreated on every unrelated re-render — the
  // stagger effect in MasteryDelta keys off array identity, so an unstable
  // array would silently restart the reveal animation on any parent re-render.
  // Must sit above the early returns below: Hooks can't be called
  // conditionally, and this component returns early while loading/erroring.
  const masteryDeltaRows = useMemo(
    () =>
      (submit.data?.masteryDelta ?? []).map((d) => ({
        skillId: d.skillId,
        skillName: d.skillName,
        priorBand: d.priorBand,
        posteriorBand: d.posteriorBand,
      })),
    [submit.data?.masteryDelta]
  );

  if (isLoading)
    return (
      <LoadingPanel
        label="Building your diagnostic…"
        lines={4}
      />
    );
  if (isError)
    return (
      <EmptyState
        title="We could not load the diagnostic"
        description="Check your connection and try again."
        action={<Button variant="outline">Retry</Button>}
      />
    );
  if (!data || data.questions.length === 0)
    return (
      <EmptyState
        title="No diagnostic yet"
        description="Take a diagnostic to build your baseline for this course."
      />
    );

  const allAnswered = data.questions.every((q) => selections[q.id]);
  const submitted = submit.isSuccess;

  function handleSubmit() {
    const answers: Answer[] = data!.questions.map((q) => ({
      itemId: q.id,
      choiceId: selections[q.id],
      latencyMs: Date.now() - startedAt,
    }));
    submit.mutate(answers, {
      onSuccess: (result) => {
        const byItem: Record<string, AnswerResult> = {};
        for (const r of result.results) byItem[r.itemId] = r;
        setResultsByItem(byItem);
      },
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course diagnostic</CardTitle>
      </CardHeader>
      <CardContent className="space-y-8">
        {data.questions.map((q) => {
          const result = resultsByItem[q.id];
          return (
            <div key={q.id} className="space-y-3 border-t border-border/60 pt-6 first:border-t-0 first:pt-0">
              <p className="font-medium">{q.prompt}</p>
              <div className="flex flex-col gap-2">
                {q.choices.map((c) => (
                  <label
                    key={c.id}
                    className="flex min-w-0 cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2 text-sm transition-colors has-[:checked]:border-brand-orange has-[:checked]:bg-brand-orange/5 hover:border-brand-orange/40 hover:bg-accent/40"
                  >
                    <input
                      type="radio"
                      name={q.id}
                      value={c.id}
                      disabled={submitted}
                      checked={selections[q.id] === c.id}
                      onChange={() => setSelections((s) => ({ ...s, [q.id]: c.id }))}
                      className="size-4 shrink-0"
                    />
                    <span className="min-w-0 flex-1 break-words leading-relaxed">{c.label}</span>
                  </label>
                ))}
              </div>
              {result ? (
                <p className={result.correct ? "text-sm font-medium text-brand-green" : "text-sm font-medium text-destructive"}>
                  {result.correct ? "Correct." : "Not quite."} {result.explanation}
                </p>
              ) : null}
            </div>
          );
        })}

        {!submitted ? (
          <Button variant="orange" disabled={!allAnswered || submit.isPending} onClick={handleSubmit}>
            {submit.isPending ? "Submitting…" : "Submit diagnostic"}
          </Button>
        ) : (
          <div className="space-y-4">
            <p className="text-sm font-medium">
              You got {submit.data?.correctCount} of {submit.data?.total} correct.
            </p>
            {masteryDeltaRows.length > 0 ? <MasteryDelta rows={masteryDeltaRows} /> : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
