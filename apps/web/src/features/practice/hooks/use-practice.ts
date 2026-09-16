import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPracticeSetFromItems,
  fetchNextPracticeItem,
  fetchPracticeSet,
  fetchPracticeSetById,
  fetchPracticeSets,
  submitPracticeAttempt,
} from "@/features/practice/api/practice.api";

// Quick practice: fetch the next item for a given skill, submit an
// attempt, then refetch the next item so the loop continues.
// Retained as the single-item path (see the set hook below for the session
// default). Nothing outside PracticePanel calls it.
export function useNextPracticeItem(courseId: string, skillId?: string) {
  return useQuery({
    queryKey: ["practice", courseId, "next", skillId ?? "auto"],
    queryFn: () => fetchNextPracticeItem(courseId, skillId),
  });
}

// The session path: one batched set of items for the skill, fetched once.
// The panel holds the set and advances through it locally — answering is
// instant because the next item already exists client-side, which is the
// whole point of batching (server-side generation is the ~10s cost, not
// rendering). A new set is only fetched when the student exhausts this one
// ("Generate another set") or changes topic, both of which are explicit
// actions, so this query never refetches mid-session and the set can't shift
// under an in-progress answer.
//
// Cache key is per skill and marked staleTime: Infinity for the same reason:
// a background refetch would swap the batch out from under the student.
// Invalidation is not needed on submit — evidence/mastery live on other keys
// (twin, next-up, gamification), which useSubmitPractice already handles.
export function usePracticeSet(courseId: string, skillId: string, size = 5) {
  return useQuery({
    queryKey: ["practice", courseId, "set", skillId, size],
    queryFn: () => fetchPracticeSet(courseId, { skillId, size }),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}

// Load a SAVED set by id — test mode re-entering a set the student already has
// (the study->test bridge handoff, or a retake). Mirrors usePracticeSet's
// caching discipline: the set is immutable once loaded.
export function usePracticeSetById(courseId: string, setId: string | null) {
  return useQuery({
    queryKey: ["practice", courseId, "saved-set", setId],
    queryFn: () => fetchPracticeSetById(courseId, setId as string),
    enabled: Boolean(setId),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}

// The retake list for a skill. Plain read; refetch on focus is fine here.
export function usePracticeSets(courseId: string, skillId?: string) {
  return useQuery({
    queryKey: ["practice", courseId, "sets", skillId ?? "all"],
    queryFn: () => fetchPracticeSets(courseId, skillId),
  });
}

// The study -> test bridge: group studied items into a set. Not a query — it
// is a one-shot action the caller then navigates with, so a mutation is the
// honest shape. Invalidates the retake list so a new set shows up there.
export function useCreateSetFromItems(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemIds: string[]) => createPracticeSetFromItems(courseId, itemIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["practice", courseId, "sets"] });
    },
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
