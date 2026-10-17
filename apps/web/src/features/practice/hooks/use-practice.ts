import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPracticeSet,
  fetchPracticeSetById,
  fetchPracticeSetResults,
  fetchPracticeSets,
  startRetake,
  submitPracticeAttempt,
} from "@/features/practice/api/practice.api";
import type { PracticeSavedSet, PracticeSet } from "@/features/practice/schema/practice.schema";

const POLL_INTERVAL_MS = 5_000;

// The session path creates one durable set, then polls its stable detail URL.
// The query function deliberately switches from POST to GET after the first
// generating response; polling must never create a second quiz set.
export function usePracticeSet(
  courseId: string,
  skillId: string,
  size = 5,
  options: { enabled?: boolean; sessionId?: string } = {},
) {
  const queryClient = useQueryClient();
  const queryKey = ["practice", courseId, "set", skillId, size, options.sessionId ?? "legacy"];
  return useQuery({
    queryKey,
    enabled: options.enabled ?? true,
    queryFn: async (): Promise<PracticeSet | PracticeSavedSet> => {
      const current = queryClient.getQueryData<PracticeSet>(queryKey);
      if (current?.setId) {
        return fetchPracticeSetById(courseId, current.setId);
      }
      return fetchPracticeSet(courseId, { skillId, size });
    },
    refetchOnReconnect: false,
    staleTime: (query) =>
      query.state.data?.status === "generating" || query.state.data?.status === "preparing" ? 0 : Infinity,
    refetchInterval: (query) =>
      query.state.data?.status === "generating" || query.state.data?.status === "preparing" ? POLL_INTERVAL_MS : false,
    refetchOnWindowFocus: (query) =>
      query.state.data?.status === "generating",
  });
}

// Load a SAVED set by id — test mode re-entering a set the student already has
// (a saved set or a retake). Mirrors usePracticeSet's
// caching discipline: the set is immutable once loaded.
export function usePracticeSetById(courseId: string, setId: string | null) {
  return useQuery({
    queryKey: ["practice", courseId, "saved-set", setId],
    queryFn: () => fetchPracticeSetById(courseId, setId as string),
    enabled: Boolean(setId),
    staleTime: (query) =>
      query.state.data?.status === "generating" ? 0 : Infinity,
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? POLL_INTERVAL_MS : false,
    refetchOnWindowFocus: (query) =>
      query.state.data?.status === "generating",
  });
}

export function usePracticeSetResults(
  courseId: string,
  setId: string | null,
  enabled = true,
  attemptId?: string,
) {
  return useQuery({
    queryKey: ["practice", courseId, "set-results", setId, attemptId],
    queryFn: () => fetchPracticeSetResults(courseId, setId as string, attemptId),
    enabled: Boolean(courseId && setId && enabled),
    staleTime: 0,
  });
}

export function useStartRetake(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (setId: string) => startRetake(courseId, setId),
    onSuccess: (_result, setId) => {
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "set-results", setId] });
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "sets"] });
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "saved-set", setId], refetchType: "none" });
    },
  });
}

// The retake list for a skill. Plain read; refetch on focus is fine here.
export function usePracticeSets(courseId: string, skillId?: string) {
  return useQuery({
    queryKey: ["practice", courseId, "sets", skillId ?? "all"],
    queryFn: () => fetchPracticeSets(courseId, skillId),
  });
}

// "Generate new set" from the Test tab browser: a one-shot generation the
// caller then navigates from (to the new set's detail view), not a query — so
// a mutation, and it invalidates the set list so the new set appears there.
// This is the same POST /set the session path uses; the only difference is
// who consumes the result (browse-then-start vs. jump-straight-in).
export function useGenerateSet(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { skillId: string; size?: number }) =>
      fetchPracticeSet(courseId, { skillId: args.skillId, size: args.size }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "sets"] });
    },
  });
}

export function useSubmitPractice(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      itemId: string;
      choiceId: string;
      latencyMs: number;
      setId?: string | null;
      attemptId?: string;
      sessionId: string;
      idempotencyKey: string;
    }) =>
      submitPracticeAttempt(courseId, args),
    onSuccess: (_result, args) => {
      queryClient.invalidateQueries({ queryKey: ["flashcards", courseId, "membership"] });
      queryClient.invalidateQueries({ queryKey: ["flashcards", courseId, 0] });
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "sets"] });
      if (args.setId) {
        queryClient.invalidateQueries({ queryKey: ["practice", courseId, "saved-set", args.setId], refetchType: "none" });
      }
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
