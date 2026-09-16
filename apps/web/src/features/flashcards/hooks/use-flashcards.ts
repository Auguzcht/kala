import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchFlashcardDeck,
  reviewFlashcard,
} from "@/features/flashcards/api/flashcards.api";

export function useFlashcardDeck(courseId: string, limit = 10, skillId?: string) {
  return useQuery({
    queryKey: ["flashcards", courseId, limit, skillId ?? "auto"],
    queryFn: () => fetchFlashcardDeck(courseId, limit, skillId),
  });
}

// Study is a self-mark: the server advances the SRS schedule and writes an
// evidence_event (so XP and the research export move), but it does NOT touch
// mastery — self-report is not assessment. So this invalidates only the
// gamified header, not the twin or next-up: mastery genuinely did not change,
// and refetching those would be a no-op round trip on every card.
// The deck query is deliberately NOT invalidated — a refetch would reorder
// cards mid-session (due_at moved) and drift the local index. The deck
// refreshes on the explicit "Reload deck" action.
export function useReviewFlashcard(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      itemId: string;
      remembered: boolean;
      latencyMs: number;
    }) => reviewFlashcard(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
