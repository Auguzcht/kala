import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchFlashcardDeck,
  reviewFlashcard,
  revealFlashcard,
} from "@/features/flashcards/api/flashcards.api";

export function useFlashcardDeck(courseId: string, limit = 10) {
  return useQuery({
    queryKey: ["flashcards", courseId, limit],
    queryFn: () => fetchFlashcardDeck(courseId, limit),
  });
}

// Review and reveal both write evidence, move the tracer, and advance the
// schedule, so they invalidate the derived surfaces: mastery and the
// gamified header. The deck query is deliberately NOT invalidated — a
// refetch would reorder cards mid-session (due_at moved) and drift the
// local index. The deck refreshes on the explicit "Reload deck" action.
export function useReviewFlashcard(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      itemId: string;
      choiceId: string;
      latencyMs: number;
      hintsUsed: number;
    }) => reviewFlashcard(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mastery", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}

export function useRevealFlashcard(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { itemId: string; latencyMs: number }) =>
      revealFlashcard(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mastery", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
