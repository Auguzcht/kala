import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchNextUp, fetchTwin } from "@/features/twin/api/twin.api";

// staleTime + keepPreviousData: without these, isLoading briefly went true
// on every refetch of an existing query (finishing a practice/lesson session
// invalidates next-up and twin, and a route change back to Home remounts
// this hook), which is what made the "Next Up" card and twin snapshot flash
// to a skeleton and back instead of just updating in place once the new
// data arrived. keepPreviousData keeps rendering the last known data (and
// isLoading stays false) while the background refetch is in flight, so the
// card's TEXT updates when new data lands instead of the whole card
// disappearing and reappearing.
export function useTwin(courseId: string) {
  return useQuery({
    queryKey: ["twin", courseId],
    queryFn: () => fetchTwin(courseId),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });
}

export function useNextUp(courseId: string) {
  return useQuery({
    queryKey: ["next-up", courseId],
    queryFn: () => fetchNextUp(courseId),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });
}
