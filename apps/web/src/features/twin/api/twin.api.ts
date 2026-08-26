import { api } from "@/lib/api/client";
import { nextUpSchema, twinSchema, type NextUp, type Twin } from "@/features/twin/schema/twin.schema";

export async function fetchTwin(courseId: string): Promise<Twin> {
  const data = await api<unknown>(`/courses/${courseId}/twin`);
  return twinSchema.parse(data);
}

export async function fetchNextUp(courseId: string): Promise<NextUp> {
  const data = await api<unknown>(`/courses/${courseId}/next-up`);
  return nextUpSchema.parse(data);
}
