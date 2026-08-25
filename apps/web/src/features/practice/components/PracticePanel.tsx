import { useEffect, useState } from "react";
import { useNextPracticeItem, useSubmitPractice } from "@/features/practice/hooks/use-practice";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import type { PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

// Quick-practice loop: one item at a time, targeted at the student's
// weakest skill. Answering advances to the next item automatically.
export function PracticePanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useNextPracticeItem(courseId);
  const submit = useSubmitPractice(courseId);
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PracticeSubmitResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());

  useEffect(() => {
    setSelectedChoice(null);
    setLastResult(null);
    setStartedAt(Date.now());
  }, [data?.item?.id]);

  if (isLoading) return <p className="text-muted-foreground">Finding your next item…</p>;
  if (isError)
    return (
      <EmptyState
        title="We could not load practice"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (!data?.item)
    return (
      <EmptyState
        title="Nothing to practice yet"
        description="Skills for this course haven't been set up yet."
      />
    );

  const item = data.item;

  function handleAnswer(choiceId: string) {
    setSelectedChoice(choiceId);
    submit.mutate(
      { itemId: item.id, choiceId, latencyMs: Date.now() - startedAt },
      { onSuccess: (result) => setLastResult(result) }
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick practice</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {item.bloomLevel ? (
          <p className="text-xs font-medium uppercase tracking-wide text-brand-slate">
            {item.bloomLevel}
          </p>
        ) : null}
        <p className="font-medium">{item.prompt}</p>
        <div className="flex flex-col gap-2">
          {item.choices.map((c) => (
            <Button
              key={c.id}
              variant={selectedChoice === c.id ? "orange" : "outline"}
              disabled={!!lastResult}
              onClick={() => handleAnswer(c.id)}
              className="justify-start"
            >
              {c.label}
            </Button>
          ))}
        </div>

        {lastResult ? (
          <div className="space-y-3">
            <p className={lastResult.correct ? "text-sm font-medium text-brand-green" : "text-sm font-medium text-destructive"}>
              {lastResult.correct ? "Correct." : "Not quite."} {lastResult.explanation}
            </p>
            <Button variant="orange" onClick={() => refetch()}>
              Next item
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
