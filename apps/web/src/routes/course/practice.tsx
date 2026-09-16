import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TopicLanding } from "@/components/study/TopicLanding";
import { PracticePanel } from "@/features/practice";
import { useTwin, useNextUp } from "@/features/twin";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { ZapIcon } from "@/components/ui/zap";

export const Route = createFileRoute("/course/practice")({
  component: PracticePage,
});

function PracticePage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const { data: nextUp } = useNextUp(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  if (skillId) {
    return (
      <PracticePanel
        courseId={courseId}
        skillId={skillId}
        onExit={() => setSkillId(null)}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Practice"
        title="Choose a topic"
        description="One item at a time, graded on the spot."
      />
      <TopicLanding
        isLoading={isLoading}
        skills={twin?.skills ?? []}
        onChoose={setSkillId}
        caption="quick, graded reps"
        gridId="tour-practice-picker"
        recommended={
          nextUp?.next ? (
            <button
              id="tour-practice-recommended"
              type="button"
              onClick={() => setSkillId(nextUp.next!.skillId)}
              className="flex w-full items-center justify-between gap-4 bg-primary px-6 py-5 text-left transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-brand-gold">
                  <ZapIcon size={12} /> Recommended
                </div>
                <p className="mt-1.5 truncate font-display text-lg font-semibold text-primary-foreground">
                  {nextUp.next.skillName}
                </p>
                <p className="mt-1 text-[13px] text-primary-foreground/70">{nextUp.next.reason}</p>
              </div>
              <ArrowRightIcon size={18} className="shrink-0 text-primary-foreground/70" />
            </button>
          ) : null
        }
      />
    </>
  );
}
