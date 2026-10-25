import { InstructorReadFailure } from "@/features/instructor/components/InstructorReadFailure";
import { LoadingRegion } from "@/components/shared/LoadingRegion";
import { useAtRisk, useStudentTwin } from "@/features/instructor";
import { TwinBody } from "@/features/twin/components/TwinBody";
import { Skeleton } from "@/components/ui/skeleton";

// Instructor drill-down: one student's twin, de-identified posture made
// visible (pseudonym + chip), needs-support reason when flagged, then the
// full twin body (readiness, radar, bands, ladder, ledger).
export function StudentDrillDown({ courseId, userId }: { courseId: string; userId: string }) {
  const twin = useStudentTwin(courseId, userId);
  const atRisk = useAtRisk(courseId);

  if (twin.isLoading) {
    return (
      <LoadingRegion className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-64 w-full" />
      </LoadingRegion>
    );
  }
  if (twin.isError || !twin.data) {
    return <InstructorReadFailure error={twin.error} retry={twin.refetch} learner />;
  }

  const flag = atRisk.data?.flags.find((f) => f.userId === userId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <span className="grid size-9 place-items-center rounded-full bg-brand-slate text-[12px] font-bold text-background">
          {twin.data.pseudonym
            .split(/\s+/)
            .slice(0, 2)
            .map((p) => p[0])
            .join("")
            .toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-lg font-semibold text-foreground">
            {twin.data.pseudonym}
          </p>
        </div>
        <span className="flex items-center gap-1.5 rounded-sm border border-brand-green/25 bg-brand-green/10 px-2 py-1 text-[11px] font-medium text-brand-green-foreground">
          <span className="size-1.5 rounded-full bg-brand-green" aria-hidden />
          De-identified before any model call · pseudonym shown to Kala
        </span>
      </div>

      {flag ? (
        <div className="border-l-[3px] border-destructive bg-destructive/5 p-3.5">
          <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-destructive">
            Needs support
          </p>
          <p className="mt-1 text-[12.5px] leading-relaxed text-foreground/80">{flag.reason}</p>
        </div>
      ) : null}

      <TwinBody key={userId} twin={twin.data} own={false} historyTargetId={userId} />
    </div>
  );
}
