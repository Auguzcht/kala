import { useDiagnostic } from "@/features/diagnostic/hooks/use-diagnostic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";

// Worked-example component. Shows the feature wiring: query hook -> UI.
export function DiagnosticPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError } = useDiagnostic(courseId);

  if (isLoading) return <p className="text-muted-foreground">Loading diagnostic…</p>;
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
        action={<Button variant="gold">Start diagnostic</Button>}
      />
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Course diagnostic</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.questions.map((q) => (
          <div key={q.id}>
            <p className="text-xs font-medium uppercase tracking-wide text-brand-teal">
              {q.bloomLevel}
            </p>
            <p className="mt-1 font-medium">{q.prompt}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
