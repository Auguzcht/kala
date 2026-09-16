import { api } from "@/lib/api/client";
import {
  practiceNextSchema,
  practiceSetSchema,
  practiceSubmitResultSchema,
  type PracticeNext,
  type PracticeSet,
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
