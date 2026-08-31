import { api } from "@/lib/api/client";
import { courseMetaSchema, type CourseMeta } from "@/features/courses/schema/courses.schema";

export async function fetchCourse(courseId: string, timeoutMs?: number): Promise<CourseMeta> {
  const data = await api<unknown>(`/courses/${courseId}`, undefined, timeoutMs);
  return courseMetaSchema.parse(data);
}
