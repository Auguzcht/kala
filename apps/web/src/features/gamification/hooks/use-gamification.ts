import { useQuery } from "@tanstack/react-query";
import { fetchGamificationSummary } from "@/features/gamification/api/gamification.api";

// The reward view is derived from immutable evidence — it only changes when
// the student produces evidence, so a long staleTime keeps the header from
// re-fetching on every navigation. Mutations that write evidence invalidate
// this key (see the flashcards / lessons hooks).
export function useGamification(courseId: string) {
  return useQuery({
    queryKey: ["gamification", courseId],
    queryFn: () => fetchGamificationSummary(courseId),
    staleTime: 60_000,
  });
}
