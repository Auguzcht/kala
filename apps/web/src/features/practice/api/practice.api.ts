import { api } from "@/lib/api/client";
import { parseApiResponse } from "@/lib/api/parse-response";
import {
  practiceNextSchema,
  practiceBridgeSetSchema,
  practiceSavedSetSchema,
  practiceSetListSchema,
  practiceSetSchema,
  practiceSubmitResultSchema,
  type PracticeNext,
  type PracticeBridgeSet,
  type PracticeSavedSet,
  type PracticeSet,
  type PracticeSetList,
  type PracticeSubmitResult,
} from "@/features/practice/schema/practice.schema";

export async function fetchNextPracticeItem(courseId: string, skillId?: string): Promise<PracticeNext> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/next${query}`);
  return parseApiResponse(practiceNextSchema, data, `/practice/${courseId}/next`);
}

// Enqueue a batch of N items for one skill, grouped under a quiz_sets row.
// The 202 response is followed by GET /sets/{set_id} polling in the hook.
export async function fetchPracticeSet(
  courseId: string,
  args: { skillId?: string; size?: number } = {}
): Promise<PracticeSet> {
  const params = new URLSearchParams();
  if (args.skillId) params.set("skill_id", args.skillId);
  if (args.size) params.set("size", String(args.size));
  const query = params.toString() ? `?${params.toString()}` : "";
  const data = await api<unknown>(
    `/practice/${courseId}/set${query}`,
    { method: "POST" },
    15_000
  );
  return parseApiResponse(practiceSetSchema, data, `/practice/${courseId}/set`);
}

// The study -> test bridge: group ALREADY-GENERATED items (the ones the
// student just studied) into a quiz set, without regenerating anything. Same
// response shape as fetchPracticeSet so the quiz surface consumes it
// identically. timeoutMs is short — this makes no model calls, it is a
// grouping write.
export async function createPracticeSetFromItems(
  courseId: string,
  itemIds: string[]
): Promise<PracticeBridgeSet> {
  const data = await api<unknown>(
    `/practice/${courseId}/set/from-items`,
    { method: "POST", body: JSON.stringify({ item_ids: itemIds }) },
    15_000
  );
  return parseApiResponse(practiceBridgeSetSchema, data, `/practice/${courseId}/set/from-items`);
}

// Load a saved set by id, so test mode can run it instead of generating.
export async function fetchPracticeSetById(
  courseId: string,
  setId: string
): Promise<PracticeSavedSet> {
  const data = await api<unknown>(`/practice/${courseId}/sets/${setId}`);
  return parseApiResponse(practiceSavedSetSchema, data, `/practice/${courseId}/sets/${setId}`);
}

// The retake list for a skill (or the whole course when skillId is omitted).
export async function fetchPracticeSets(
  courseId: string,
  skillId?: string
): Promise<PracticeSetList> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/sets${query}`);
  return parseApiResponse(practiceSetListSchema, data, `/practice/${courseId}/sets`);
}

export async function submitPracticeAttempt(
  courseId: string,
  args: { itemId: string; choiceId: string; latencyMs: number; setId?: string | null }
): Promise<PracticeSubmitResult> {
  const data = await api<unknown>(`/practice/${courseId}/submit`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      choice_id: args.choiceId,
      latency_ms: args.latencyMs,
      ...(args.setId ? { set_id: args.setId } : {}),
    }),
  });
  return parseApiResponse(practiceSubmitResultSchema, data, `/practice/${courseId}/submit`);
}
