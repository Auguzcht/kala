import { api } from "@/lib/api/client";
import { planSchema, type Plan } from "@/features/plan/schema/plan.schema";

export async function fetchPlan(courseId: string, timeoutMs?: number): Promise<Plan> {
  const data = await api<unknown>(`/courses/${courseId}/plan`, undefined, timeoutMs);
  return planSchema.parse(data);
}
