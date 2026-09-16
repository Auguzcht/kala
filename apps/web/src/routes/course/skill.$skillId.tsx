import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { useSession } from "@/lib/auth/AuthProvider";
import { SkillHub, type SkillTab } from "@/features/skill-hub";

// /course/skill/:skillId — the skill hub. The active mode lives in the URL so
// the page is linkable and the Workspace "Next up" card can deep-link straight
// to ?tab=test. `setId` enters Test on a specific saved set (a retake, or a
// study→test bridge handoff).
const skillSearchSchema = z.object({
  tab: z.enum(["lesson", "study", "test"]).optional(),
  setId: z.string().optional(),
});

export const Route = createFileRoute("/course/skill/$skillId")({
  validateSearch: skillSearchSchema,
  component: SkillHubPage,
});

function SkillHubPage() {
  const courseId = useSession()?.courseId ?? "";
  const { skillId } = Route.useParams();
  const { tab, setId } = Route.useSearch();
  const navigate = useNavigate();

  return (
    <SkillHub
      courseId={courseId}
      skillId={skillId}
      tab={tab as SkillTab | undefined}
      setId={setId}
      // Leaving a session returns to the hub landing (no tab in the URL), so
      // a refresh doesn't drop the student back into a session they exited.
      onExitSession={() =>
        navigate({ to: "/course/skill/$skillId", params: { skillId }, search: {} })
      }
    />
  );
}
