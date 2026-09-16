import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { useSession } from "@/lib/auth/AuthProvider";
import { SkillHub, type SkillTab } from "@/features/skill-hub";

// /course/skill/:skillId — the skill hub. The active mode lives in the URL so
// the page is linkable and the Workspace "Next up" card can deep-link straight
// to ?tab=test&start=1.
//
// Browse-then-commit, same shape for Study and Test: `tab` alone is the browse
// pane (which cards / which set), and `start=1` begins the session takeover.
// `setId` additionally opens one set's detail view (a retake, or a study→test
// bridge handoff) so the student sees what they're about to be tested on.
// Lesson has no browse step — there is one guided walkthrough per skill, not a
// choice — so `tab=lesson` goes straight into the lesson session.
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
      // Switch panes in place. Dropping `start`/`setId` means switching tabs
      // always lands on the new tab's browse pane, never mid-session.
      onSelectTab={(nextTab) =>
        navigate({ to, params: { skillId }, search: { tab: nextTab } })
      }
      // Open a set's detail view (or clear back to the list with "").
      onSelectSet={(nextSetId) =>
        navigate({
          to,
          params: { skillId },
          search: nextSetId ? { tab: "test", setId: nextSetId } : { tab: "test" },
        })
      }
      // Commit to the running session for the active tab. Study and Test share
      // this switch; each reads `start` only for its own tab.
      onStart={() =>
        navigate({ to, params: { skillId }, search: { tab, setId, start: true } })
      }
      // Leaving a session returns to that tab's browse pane (keeps `tab`,
      // drops `start`). Lesson has no browse pane, so it exits to Study —
      // leaving `tab=lesson` in the URL would immediately re-enter the lesson.
      onExitSession={() =>
        navigate({
          to,
          params: { skillId },
          search: { tab: tab === "lesson" || !tab ? "study" : tab },
        })
      }
    />
  );
}
