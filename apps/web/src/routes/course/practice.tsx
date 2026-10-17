import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TopicLanding } from "@/components/study/TopicLanding";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { useTwin, useNextUp } from "@/features/twin";
import { useBankStatus } from "@/features/bank";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { ZapIcon } from "@/components/ui/zap";
import { z } from "zod";

// Legacy Test entry: topic choices and saved-set links open the canonical
// skill hub browse pane, so revisiting a topic cannot resume a cached sitting.
const practiceSearchSchema = z.object({
  skillId: z.string().optional(),
  setId: z.string().optional(),
});

export const Route = createFileRoute("/course/practice")({
  validateSearch: practiceSearchSchema,
  component: PracticePage,
});

function PracticePage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const { data: bankStatus } = useBankStatus(courseId);
  const { data: nextUp } = useNextUp(courseId);
  const { skillId: searchSkillId, setId: searchSetId } = Route.useSearch();
  const navigate = useNavigate();
  useEffect(() => {
    if (!searchSkillId) return;
    void navigate({
      to: "/course/skill/$skillId",
      params: { skillId: searchSkillId },
      search: { tab: "test", setId: searchSetId },
      replace: true,
    });
  }, [searchSkillId, searchSetId, navigate]);

  function openTopic(skillId: string) {
    void navigate({ to: "/course/skill/$skillId", params: { skillId }, search: { tab: "test" } });
  }

  if (searchSkillId) return <LoadingPanel label="Opening tests…" lines={2} />;

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
        bankStatus={bankStatus}
        onChoose={openTopic}
        caption="quick, graded reps"
        gridId="tour-practice-picker"
        recommended={
          nextUp?.next ? (
            <button
              id="tour-practice-recommended"
              type="button"
              onClick={() => openTopic(nextUp.next!.skillId)}
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
