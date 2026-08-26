import { api } from "@/lib/api/client";
import { courseMetaSchema, type CourseMeta } from "@/features/courses/schema/courses.schema";

export async function fetchCourse(courseId: string): Promise<CourseMeta> {
  const data = await api<unknown>(`/courses/${courseId}`);
  return courseMetaSchema.parse(data);
}
