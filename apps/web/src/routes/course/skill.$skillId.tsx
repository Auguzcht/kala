import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { SkillHub, hubSearchSchema, type SkillTab } from "@/features/skill-hub";

// /course/skill/:skillId — the skill hub. The active mode lives in the URL so
// the page is linkable and the Workspace "Next up" card can deep-link straight
// to ?tab=test&start=1.
//
// Browse-then-commit, same shape for Study and Test: `tab` alone is the browse
// pane (which cards / which set), and `start=1` begins the session takeover.
// `setId` additionally opens one set's detail view (a saved set or a retake) so the student sees what they're about to be tested on.
// Lesson has no browse step — there is one guided walkthrough per skill, not a
// choice — so `tab=lesson` goes straight into the lesson session.

export const Route = createFileRoute("/course/skill/$skillId")({
  validateSearch: hubSearchSchema,
  component: SkillHubPage,
});

function SkillHubPage() {
  const courseId = useSession()?.courseId ?? "";
  const { skillId } = Route.useParams();
  const { tab: searchTab, setId, sessionId, attemptId, studySetId, missedItemIds, start, repeats, mode } = Route.useSearch();
  const tab = searchTab ?? "study";
  const navigate = useNavigate();
  const to = "/course/skill/$skillId" as const;

  return (
    <SkillHub
      courseId={courseId}
      skillId={skillId}
      tab={tab as SkillTab}
      setId={setId}
      sessionId={sessionId}
      attemptId={attemptId}
      studySetId={studySetId}
      missedItemIds={missedItemIds}
      includesRepeats={repeats}
      start={start}
      studyMode={mode ?? "review"}
      // Switch panes in place. Dropping `start`/`setId` means switching tabs
      // always lands on the new tab's browse pane, never mid-session.
      onSelectTab={(nextTab) =>
        navigate({ to, params: { skillId }, search: { tab: nextTab } })
      }
      // Open a set's detail view (or clear back to the list with "").
      onSelectSet={(nextSetId, includesRepeats) =>
        navigate({
          to,
          params: { skillId },
          search: nextSetId ? { tab: "test", setId: nextSetId, repeats: includesRepeats || undefined } : { tab: "test" },
        })
      }
      // Commit to the running session for the active tab. A bare skill URL
      // defaults to Study so the deck action always enters the Study session.
      onStart={(studyMode) =>
        navigate({
          to,
          params: { skillId },
          search: {
            tab,
            setId,
            repeats,
            start: true,
            ...(tab === "study" ? { mode: studyMode ?? "review" } : {}),
            ...(tab === "test" ? { sessionId: crypto.randomUUID() } : {}),
          },
        })
      }
      onStartTest={(nextSetId) =>
        navigate({
          to,
          params: { skillId },
          search: {
            tab: "test",
            setId: nextSetId ?? setId,
            start: true,
            sessionId: crypto.randomUUID(),
          },
        })
      }
      onSessionReady={(nextSetId, nextSessionId, nextAttemptId) =>
        navigate({
          to,
          params: { skillId },
          replace: true,
          search: {
            tab: "test",
            setId: nextSetId,
            repeats,
            start: true,
            sessionId: nextSessionId,
            attemptId: nextAttemptId,
          },
        })
      }
      onStudyMissedSet={(missedSetId, itemIds, reviewAttemptId) =>
        navigate({
          to,
          params: { skillId },
          search: { tab: "study", start: true, mode: "all", studySetId: missedSetId, missedItemIds: itemIds, attemptId: reviewAttemptId },
        })
      }
      onReviewMissedSet={(missedSetId) =>
        navigate({
          to,
          params: { skillId },
          search: {
            tab: "test",
            setId: missedSetId,
            attemptId,
            start: true,
            sessionId: crypto.randomUUID(),
          },
        })
      }
      // Leaving a session returns to that tab's browse pane (keeps `tab`,
      // drops `start`). Lesson has no browse pane, so it exits to Study —
      // leaving `tab=lesson` in the URL would immediately re-enter the lesson.
      onExitSession={() =>
        navigate({
          to,
          params: { skillId },
          search: { tab: tab === "lesson" ? "study" : tab },
        })
      }
    />
  );
}
