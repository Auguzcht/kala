import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { LessonStepper } from "@/features/lessons";
import { useTwin } from "@/features/twin";
import { MasteryBand } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

export const Route = createFileRoute("/course/lessons")({
  component: LessonsPage,
});

function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Guided lessons"
        title="Work through it, step by step"
        description="Kala walks you through one skill at a time — explain, check, advance. Lessons are written once and replayed, so every pass is consistent."
      />
      {skillId ? (
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => setSkillId(null)}>
            <ChevronLeft className="size-3.5" /> Choose another skill
          </Button>
          <LessonStepper courseId={courseId} skillId={skillId} />
        </div>
      ) : isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !twin || twin.skills.length === 0 ? (
        <EmptyState
          title="No skills mapped yet"
          description="Lessons are built from approved skills. Course content needs the ingest + skill-proposal pass first."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {twin.skills.map((s) => (
            <button
              key={s.skillId}
              type="button"
              onClick={() => setSkillId(s.skillId)}
              className="group border bg-card p-4 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-foreground group-hover:underline">
                  {s.name}
                </span>
                <MasteryBand band={s.band} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {s.bloomLevel ? `${s.bloomLevel} · ` : ""}guided walkthrough with checks
              </p>
            </button>
          ))}
        </div>
      )}
    </>
  );
}
