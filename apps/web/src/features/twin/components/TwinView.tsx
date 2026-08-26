import { useTwin } from "@/features/twin";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TwinBody } from "@/features/twin/components/TwinBody";

// The signature surface: the student's own twin, live and evidence-driven.
export function TwinView({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useTwin(courseId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <EmptyState
        title="We could not load your twin"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  return <TwinBody twin={data} />;
}
