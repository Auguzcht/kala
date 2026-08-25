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
  });
}

export function useSubmitDiagnostic(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answers: Answer[]) => submitDiagnostic(courseId, answers),
    onSuccess: () => {
      // Mastery moved: invalidate anything reading it (dashboard, twin).
      queryClient.invalidateQueries({ queryKey: ["mastery", courseId] });
    },
  });
}
