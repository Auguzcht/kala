import { api } from "@/lib/api/client";
import {
  practiceNextSchema,
  practiceSubmitResultSchema,
  type PracticeNext,
  type PracticeSubmitResult,
} from "@/features/practice/schema/practice.schema";

export async function fetchNextPracticeItem(courseId: string, skillId?: string): Promise<PracticeNext> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/next${query}`);
  return practiceNextSchema.parse(data);
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
