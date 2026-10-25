import { useInfiniteQuery } from "@tanstack/react-query";
import { useSession } from "@/lib/auth/AuthProvider";
import { fetchEvidenceHistory } from "@/features/twin/api/evidence-history.api";
import type { EvidenceEvent } from "@/features/twin/schema/twin.schema";

export function useEvidenceHistory(courseId: string, targetId?: string) {
  const session = useSession();
  const key = ["evidence-history", session?.institutionId, session?.userId,
    targetId ?? session?.userId, courseId, targetId ? "staff" : "own"];
  const query = useInfiniteQuery({
    queryKey: key,
    initialPageParam: null as string | null,
    // TanStack stores cursor identity in pageParams alongside each cached page.
    queryFn: ({ pageParam }) => fetchEvidenceHistory(courseId, targetId, pageParam),
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: !!session && !!courseId && (!!targetId || session.role === "student"),
    retry: false,
    staleTime: 30_000,
  });
  const seen = new Set<string>();
  const events: EvidenceEvent[] = [];
  for (const page of query.data?.pages ?? []) {
    for (const event of page.evidence) {
      if (!seen.has(event.id)) { seen.add(event.id); events.push(event); }
    }
  }
  return { ...query, events, scopeKey: JSON.stringify(key) };
}
