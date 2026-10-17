import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TopicLanding } from "@/components/study/TopicLanding";
import { useTwin } from "@/features/twin";
import { useBankStatus } from "@/features/bank";

export const Route = createFileRoute("/course/lessons")({
  component: LessonsPage,
});

function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const { data: bankStatus } = useBankStatus(courseId);
  const navigate = useNavigate();

  return (
    <>
      <PageHeader
        eyebrow="Lessons"
        title="Choose a topic"
      />
      <TopicLanding
        isLoading={isLoading}
        skills={twin?.skills ?? []}
        bankStatus={bankStatus}
        onChoose={(skillId) => navigate({ to: "/course/skill/$skillId", params: { skillId }, search: { tab: "lesson" } })}
        gridId="tour-lessons-picker"
        firstCardId="tour-lessons-first-card"
      />
    </>
  );
}
