import { api } from "@/lib/api/client";
import {
  practiceNextSchema,
  practiceSavedSetSchema,
  practiceSetListSchema,
  practiceSetSchema,
  practiceSubmitResultSchema,
  type PracticeNext,
  type PracticeSavedSet,
  type PracticeSet,
  type PracticeSetList,
  type PracticeSubmitResult,
} from "@/features/practice/schema/practice.schema";

export async function fetchNextPracticeItem(courseId: string, skillId?: string): Promise<PracticeNext> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/next${query}`);
  return practiceNextSchema.parse(data);
}

// A batch of N items for one skill, generated concurrently server-side and
// grouped under a quiz_sets row. The session path: the hook holds the whole
// set and advances locally, so N questions cost one generation round trip
// instead of N. `skillId` omitted resolves to the student's weakest skill.
// timeoutMs is generous because this awaits N concurrent model calls in one
// request — same class as lesson generation, not a plain read.
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
    60_000
  );
  return practiceSetSchema.parse(data);
}

// The study -> test bridge: group ALREADY-GENERATED items (the ones the
// student just studied) into a quiz set, without regenerating anything. Same
// response shape as fetchPracticeSet so the quiz surface consumes it
// identically. timeoutMs is short — this makes no model calls, it is a
// grouping write.
export async function createPracticeSetFromItems(
  courseId: string,
  itemIds: string[]
): Promise<PracticeSet> {
  const data = await api<unknown>(
    `/practice/${courseId}/set/from-items`,
    { method: "POST", body: JSON.stringify({ item_ids: itemIds }) },
    15_000
  );
  return practiceSetSchema.parse(data);
}

// Load a saved set by id, so test mode can run it instead of generating.
export async function fetchPracticeSetById(
  courseId: string,
  setId: string
): Promise<PracticeSavedSet> {
  const data = await api<unknown>(`/practice/${courseId}/sets/${setId}`);
  return practiceSavedSetSchema.parse(data);
}

// The retake list for a skill (or the whole course when skillId is omitted).
export async function fetchPracticeSets(
  courseId: string,
  skillId?: string
): Promise<PracticeSetList> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/sets${query}`);
  return practiceSetListSchema.parse(data);
}

export async function submitPracticeAttempt(
  courseId: string,
  args: { itemId: string; choiceId: string; latencyMs: number }
): Promise<PracticeSubmitResult> {
  const data = await api<unknown>(`/practice/${courseId}/submit`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      choice_id: args.choiceId,
      latency_ms: args.latencyMs,
    }),
  });
  return practiceSubmitResultSchema.parse(data);
}
