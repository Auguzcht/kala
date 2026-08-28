import { useMutation } from "@tanstack/react-query";
import { askTutor } from "@/features/tutor/api/tutor.api";
import type { TutorStyle } from "@/features/tutor/schema/tutor.schema";

// Stateless per-turn ask: history lives client-side (see TutorChat), the
// backend only ever sees the current question plus RAG context.
export function useAskTutor(courseId: string) {
  return useMutation({
    mutationFn: (question: string) => askTutor(courseId, question),
  });
}

// Same grounded ask with an explicit register for the follow-up chips
// (Hint = eli5 framing, Explain = detail framing). Used by surfaces that
// re-answer the same grounded context rather than a chat transcript.
export function useTutorAsk(courseId: string) {
  return useMutation({
    mutationFn: (args: { question: string; style?: TutorStyle }) =>
      askTutor(courseId, args.question, args.style ?? "default"),
  });
}
