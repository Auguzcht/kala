import { api } from "@/lib/api/client";
import {
  tutorAskResultSchema,
  type TutorAskResult,
  type TutorStyle,
} from "@/features/tutor/schema/tutor.schema";

export async function askTutor(
  courseId: string,
  question: string,
  style: TutorStyle = "default"
): Promise<TutorAskResult> {
  const data = await api<unknown>("/tutor/ask", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, question, style }),
  });
  return tutorAskResultSchema.parse(data);
}
