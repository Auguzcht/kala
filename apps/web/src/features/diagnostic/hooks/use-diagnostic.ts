import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchDiagnostic,
  fetchDiagnosticStatus,
  submitDiagnostic,
} from "@/features/diagnostic/api/diagnostic.api";
import type { Answer } from "@/features/diagnostic/schema/diagnostic.schema";

// Feature-specific hooks live in the feature, not in src/hooks.
export function useDiagnostic(courseId: string) {
  return useQuery({
    queryKey: ["diagnostic", courseId],
    queryFn: () => fetchDiagnostic(courseId),
    // The diagnostic is a fixed baseline instrument (one question per topic,
    // reused across fetches — see routers/diagnostic.py's idempotency fix),
    // not a randomized quiz, so there is nothing to gain from re-fetching it
    // frequently within a session.
    staleTime: 5 * 60_000,
  });
}

// Cheap due-check (no generation server-side), used for the sidebar badge
// and the workspace notice, not for the diagnostic screen's own content —
// that still calls useDiagnostic. A short staleTime keeps a freshly-loaded
// workspace from showing a stale badge without polling aggressively.
export function useDiagnosticStatus(courseId: string) {
  return useQuery({
    queryKey: ["diagnostic-status", courseId],
    queryFn: () => fetchDiagnosticStatus(courseId),
    staleTime: 60_000,
  });
}

export function useSubmitDiagnostic(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answers: Answer[]) => submitDiagnostic(courseId, answers),
    onSuccess: () => {
      // Mastery moved: invalidate the twin (per-skill estimates + readiness)
      // and next-up (Home's recommendation). ("mastery" was invalidated
      // here before; no query anywhere in the app uses that key.) Also
      // invalidate the due-check and, critically, the diagnostic question
      // list itself — without this last one, the 5-minute staleTime kept
      // serving the just-answered question set on any revisit within that
      // window, which looked like the submission never saved and allowed
      // resubmitting the same skills into duplicate evidence rows.
      queryClient.invalidateQueries({ queryKey: ["twin", courseId] });
      queryClient.invalidateQueries({ queryKey: ["next-up", courseId] });
      queryClient.invalidateQueries({ queryKey: ["diagnostic-status", courseId] });
      // Mark the question list stale WITHOUT refetching it here: the panel
      // is mounted mid-reveal right now and the refetch would resolve to an
      // empty question set (evidence just written), racing the reveal. The
      // guard in DiagnosticPanel also protects against that data swap, but
      // there is no reason to fire a network round-trip nobody needs — the
      // query is still marked invalidated, so the next genuine visit to the
      // diagnostic refetches fresh.
      queryClient.invalidateQueries({
        queryKey: ["diagnostic", courseId],
        refetchType: "none",
      });
    },
  });
}
