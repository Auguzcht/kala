import { useQuery } from "@tanstack/react-query";
import { fetchPlan } from "@/features/plan/api/plan.api";

export function usePlan(courseId: string) {
  return useQuery({
    queryKey: ["plan", courseId],
    queryFn: () => fetchPlan(courseId),
    enabled: !!courseId,
  });
}
