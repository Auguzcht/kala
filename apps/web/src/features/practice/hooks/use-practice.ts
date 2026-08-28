import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchNextPracticeItem, submitPracticeAttempt } from "@/features/practice/api/practice.api";

// Quick practice: fetch the next item for the student's weakest skill,
// submit an attempt, then refetch the next item so the loop continues.
export function useNextPracticeItem(courseId: string) {
  return useQuery({
    queryKey: ["practice", courseId, "next"],
    queryFn: () => fetchNextPracticeItem(courseId),
  });
}

export function useSubmitPractice(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { itemId: string; choiceId: string; latencyMs: number }) =>
      submitPracticeAttempt(courseId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "next"] });
      // "mastery" was invalidated here before, but no query in the app ever
      // uses that key — it did nothing. The queries that actually need to
      // refresh after evidence changes mastery are the twin (per-skill
      // estimates + readiness) and next-up (the weakest-skill
      // recommendation on Home), so those are what get invalidated now.
      queryClient.invalidateQueries({ queryKey: ["twin", courseId] });
      queryClient.invalidateQueries({ queryKey: ["next-up", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
