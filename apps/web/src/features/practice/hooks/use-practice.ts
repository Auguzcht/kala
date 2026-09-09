import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchNextPracticeItem, submitPracticeAttempt } from "@/features/practice/api/practice.api";

// Quick practice: fetch the next item for the student's weakest skill (or
// the topic picker's explicit override), submit an attempt, then refetch
// the next item so the loop continues.
export function useNextPracticeItem(courseId: string, skillId?: string) {
  return useQuery({
    queryKey: ["practice", courseId, "next", skillId ?? "auto"],
    queryFn: () => fetchNextPracticeItem(courseId, skillId),
    // Switching topics changes the query key entirely (a genuinely
    // different query, not a refetch of the same one), so without this the
    // whole panel — picker included — would flash to a loading skeleton on
    // every topic change. Keep the last topic's item on screen until the
    // new one lands instead.
    placeholderData: keepPreviousData,
  });
}

export function useSubmitPractice(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { itemId: string; choiceId: string; latencyMs: number }) =>
      submitPracticeAttempt(courseId, args),
    onSuccess: () => {
      // refetchType: "none" — mark stale, but do NOT auto-refetch. The
      // "Next item" button already calls refetch() explicitly when the
      // student is actually ready to advance; without this, invalidating
      // an ACTIVE query fires an immediate background refetch, and
      // next_item generates a genuinely new item on every call, so the
      // graded result the student is still looking at gets swapped out
      // (and reset by the [data?.item?.id] effect) within moments of
      // appearing.
      queryClient.invalidateQueries({
        queryKey: ["practice", courseId, "next"],
        refetchType: "none",
      });
      // "mastery" was invalidated here before, but no query in the app ever
      // uses that key — it did nothing. The queries that actually need to
      // refresh after evidence changes mastery are the twin (per-skill
      // estimates + readiness) and next-up (the weakest-skill
      // recommendation on Home), so those are what get invalidated now.
      // These three aren't mounted underneath the still-visible graded
      // result, so an active refetch here carries none of the same risk.
      queryClient.invalidateQueries({ queryKey: ["twin", courseId] });
      queryClient.invalidateQueries({ queryKey: ["next-up", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
