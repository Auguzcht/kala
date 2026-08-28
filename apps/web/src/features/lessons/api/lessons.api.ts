import { api } from "@/lib/api/client";
import {
  lessonSchema,
  lessonCheckResultSchema,
  type Lesson,
  type LessonCheckResult,
} from "@/features/lessons/schema/lessons.schema";

export async function fetchLesson(courseId: string, skillId: string): Promise<Lesson> {
  const data = await api<unknown>(`/lessons/${courseId}/skill/${skillId}`);
  return lessonSchema.parse(data);
}

export async function submitStepCheck(
  courseId: string,
  stepId: string,
  args: { itemId: string; choiceId: string; latencyMs: number }
): Promise<LessonCheckResult> {
  const data = await api<unknown>(`/lessons/${courseId}/steps/${stepId}/check`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      choice_id: args.choiceId,
      latency_ms: args.latencyMs,
    }),
  });
  return lessonCheckResultSchema.parse(data);
}
