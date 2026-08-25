import { api } from "@/lib/api/client";
import { tutorAskResultSchema, type TutorAskResult } from "@/features/tutor/schema/tutor.schema";

export async function askTutor(courseId: string, question: string): Promise<TutorAskResult> {
  const data = await api<unknown>("/tutor/ask", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, question }),
  });
  return tutorAskResultSchema.parse(data);
}
