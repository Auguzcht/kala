import { useMutation } from "@tanstack/react-query";
import { askTutor } from "@/features/tutor/api/tutor.api";

// Stateless per-turn ask: history lives client-side (see TutorChat), the
// backend only ever sees the current question plus RAG context.
export function useAskTutor(courseId: string) {
  return useMutation({
    mutationFn: (question: string) => askTutor(courseId, question),
  });
}
