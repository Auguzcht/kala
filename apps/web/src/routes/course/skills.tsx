import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TopicLanding } from "@/components/study/TopicLanding";
import { useTwin } from "@/features/twin";

// The skill picker — the rail's "Skills" entry. This is Kala's "materials"
// view: skills grouped by topic (moduleRef), each card opening the skill hub
// where Lesson / Study / Test live (Checkpoint 3, Step 3). It replaces the
// three separate mode destinations the rail used to carry.
//
// The old /course/lessons, /course/practice, /course/flashcards routes still
// exist as direct per-mode entries (the student tour and deep links use them);
// this is the browse-in path that leads to the hub.
export const Route = createFileRoute("/course/skills")({
  component: SkillsPage,
});

function SkillsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const navigate = useNavigate();

  return (
    <>
      <PageHeader eyebrow="Skills" title="Choose a skill" />
      <TopicLanding
        isLoading={isLoading}
        skills={twin?.skills ?? []}
        onChoose={(skillId) =>
          navigate({ to: "/course/skill/$skillId", params: { skillId }, search: {} })
        }
        caption="lesson · study · test"
        gridId="tour-skills-picker"
        firstCardId="tour-skills-first-card"
      />
    </>
  );
}
