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
    }) => submitStepCheck(courseId, args.stepId, args),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mastery", courseId] });
      queryClient.invalidateQueries({ queryKey: ["gamification", courseId] });
    },
  });
}
