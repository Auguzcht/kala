import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchFlashcardDeck,
  fetchFlashcardMembership,
  reviewFlashcard,
} from "@/features/flashcards/api/flashcards.api";

export function useFlashcardDeck(
  courseId: string,
  limit = 10,
  skillId?: string,
  mode?: "review" | "all",
  offset = 0,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    enabled: options.enabled ?? true,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryKey: ["flashcards", courseId, limit, skillId ?? "auto", mode ?? "legacy", offset],
    queryFn: () => fetchFlashcardDeck(courseId, limit, skillId, mode, offset),
  });
}

/** Explicit completion refresh keeps due/new selection even after Study all. */
export function useGetNewFlashcards(courseId: string, skillId?: string) {
  const queryClient = useQueryClient();
  return () => queryClient.fetchQuery({
    queryKey: ["flashcards", courseId, 20, skillId ?? "auto", "review", 0],
    queryFn: () => fetchFlashcardDeck(courseId, 20, skillId, "review", 0),
    staleTime: 0,
  });
}

export function useFlashcardMembership(courseId: string, skillId: string) {
  return useQuery({
    queryKey: ["flashcards", courseId, "membership", skillId],
    queryFn: () => fetchFlashcardMembership(courseId, skillId),
    enabled: Boolean(courseId && skillId),
    refetchInterval: (query) => query.state.data?.cards.some((card) => card.state !== "new" && !card.due && card.dueAt) ? 60_000 : false,
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
      sessionId: string;
      idempotencyKey: string;
    }) => reviewFlashcard(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
      queryClient.invalidateQueries({ queryKey: ["flashcards", courseId, 0] });
      queryClient.invalidateQueries({ queryKey: ["flashcards", courseId, "membership"] });
    },
  });
}
