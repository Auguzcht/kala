import { useQuery } from "@tanstack/react-query";
import { fetchNextUp, fetchTwin } from "@/features/twin/api/twin.api";

export function useTwin(courseId: string) {
  return useQuery({
    queryKey: ["twin", courseId],
    queryFn: () => fetchTwin(courseId),
  });
}

export function useNextUp(courseId: string) {
  return useQuery({
    queryKey: ["next-up", courseId],
    queryFn: () => fetchNextUp(courseId),
  });
}
