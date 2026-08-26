import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { Heatmap, AtRiskList, useHeatmap } from "@/features/instructor";
import { MasteryRing } from "@/components/kala";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/class/")({
  component: ClassDashboard,
});

function ClassDashboard() {
  const courseId = useSession()?.courseId ?? "";
  const { data: heatmap } = useHeatmap(courseId);

  return (
    <>
      <PageHeader
        eyebrow="Instructor dashboard"
        title="Class overview"
        description="Cohort mastery across the Bloom's taxonomy, needs-support flags with their reasons, and a per-student twin for every drill-down."
      />

      <div className="flex flex-wrap items-start gap-6">
        <div className="min-w-0 flex-1 space-y-6">
          <div id="heatmap-panel">
            <Heatmap courseId={courseId} />
          </div>

          <div id="cohort-readiness">
            <Card className="flex items-center gap-5 px-6 py-5">
              {heatmap ? (
                <MasteryRing
                  estimate={heatmap.cohortReadiness}
                  size={96}
                  strokeWidth={9}
                  label="Cohort readiness"
                />
              ) : (
                <Skeleton className="size-24 rounded-full" />
              )}
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-foreground">Cohort readiness</p>
                <p className="mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">
                  Weighted to the midterm blueprint. A heuristic estimate from evidence to date —
                  not a grade prediction.
                </p>
              </div>
            </Card>
          </div>
        </div>

        <div id="at-risk-list" className="w-full max-w-sm shrink-0">
          <AtRiskList courseId={courseId} />
        </div>
      </div>
    </>
  );
}
