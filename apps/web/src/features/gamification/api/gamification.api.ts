import { api } from "@/lib/api/client";
import {
  gamificationSummarySchema,
  type GamificationSummary,
} from "@/features/gamification/schema/gamification.schema";

export async function fetchGamificationSummary(courseId: string): Promise<GamificationSummary> {
  const data = await api<unknown>(`/gamification/${courseId}/summary`);
  return gamificationSummarySchema.parse(data);
}
