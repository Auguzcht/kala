import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchFlashcardDeck, reviewFlashcard } from "@/features/flashcards/api/flashcards.api";

export function useFlashcardDeck(courseId: string, limit = 5) {
  return useQuery({
    queryKey: ["flashcards", courseId, limit],
    queryFn: () => fetchFlashcardDeck(courseId, limit),
  });
}

export function useReviewFlashcard(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { itemId: string; knewIt: boolean; latencyMs: number }) =>
      reviewFlashcard(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mastery", courseId] });
    },
  });
}
