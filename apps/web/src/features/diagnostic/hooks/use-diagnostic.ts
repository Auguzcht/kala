import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchDiagnostic,
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

export function useSubmitDiagnostic(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answers: Answer[]) => submitDiagnostic(courseId, answers),
    onSuccess: () => {
      // Mastery moved: invalidate the twin (per-skill estimates + readiness)
      // and next-up (Home's recommendation). ("mastery" was invalidated
      // here before; no query anywhere in the app uses that key.)
      queryClient.invalidateQueries({ queryKey: ["twin", courseId] });
      queryClient.invalidateQueries({ queryKey: ["next-up", courseId] });
    },
  });
}
