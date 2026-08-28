import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchLesson, submitStepCheck } from "@/features/lessons/api/lessons.api";

export function useLesson(courseId: string, skillId: string | null) {
  return useQuery({
    queryKey: ["lesson", courseId, skillId],
    queryFn: () => fetchLesson(courseId, skillId as string),
    enabled: Boolean(skillId),
    // A first open races another student's generation: keep polling while
    // the backend reports the lesson is still being written.
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 2000 : false,
    // Lessons are "written once and replayed" (the page's own copy) — a
    // ready lesson's content never changes, so there is no reason to treat
    // it as stale and re-fetch every time a student leaves and re-opens the
    // same skill. refetchInterval above still forces its own polling while
    // a lesson is actively generating, independent of this.
    staleTime: 5 * 60_000,
  });
}

export function useSubmitStepCheck(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      stepId: string;
      itemId: string;
      choiceId: string;
      latencyMs: number;
      hintsUsed: number;
    }) => submitStepCheck(courseId, args.stepId, args),
    onSuccess: () => {
      // "mastery" was invalidated here before, but no query in the app ever
      // uses that key. twin + next-up are what actually need to refresh.
      queryClient.invalidateQueries({ queryKey: ["twin", courseId] });
      queryClient.invalidateQueries({ queryKey: ["next-up", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
