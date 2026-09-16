import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { useSession } from "@/lib/auth/AuthProvider";
import { SkillHub, type SkillTab } from "@/features/skill-hub";

// /course/skill/:skillId — the skill hub. The active mode lives in the URL so
// the page is linkable and the Workspace "Next up" card can deep-link straight
// to ?tab=test&start=1.
//
// Test tab has two beats: `setId` opens a set's detail view (browse), and
// `start=1` commits to the graded run. That split is deliberate — a graded
// test moves mastery, so it is an explicit choice rather than the accidental
// consequence of tapping a card in a list. `setId` also carries a study→test
// bridge handoff, which lands on the detail view so the student still sees
// what they're about to be tested on.
const skillSearchSchema = z.object({
  tab: z.enum(["lesson", "study", "test"]).optional(),
  setId: z.string().optional(),
  start: z.coerce.boolean().optional(),
});

export const Route = createFileRoute("/course/skill/$skillId")({
  validateSearch: skillSearchSchema,
  component: SkillHubPage,
});

function SkillHubPage() {
  const courseId = useSession()?.courseId ?? "";
  const { skillId } = Route.useParams();
  const { tab, setId, start } = Route.useSearch();
  const navigate = useNavigate();
  const to = "/course/skill/$skillId" as const;

  return (
    <SkillHub
      courseId={courseId}
      skillId={skillId}
      tab={tab as SkillTab | undefined}
      setId={setId}
      start={start}
      // Open a set's detail view (or clear back to the list with "").
      onSelectSet={(nextSetId) =>
        navigate({
          to,
          params: { skillId },
          search: nextSetId ? { tab: "test", setId: nextSetId } : { tab: "test" },
        })
      }
      // Commit to the graded run on the open set.
      onStart={() =>
        navigate({ to, params: { skillId }, search: { tab: "test", setId, start: true } })
      }
      // Leaving a session returns to the hub landing (no tab in the URL), so
      // a refresh doesn't drop the student back into a session they exited.
      onExitSession={() => navigate({ to, params: { skillId }, search: {} })}
    />
  );
}
