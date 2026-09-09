import { api } from "@/lib/api/client";
import {
  tutorAskResultSchema,
  tutorConversationSchema,
  tutorConversationDetailSchema,
  tutorConversationListSchema,
  type TutorAskResult,
  type TutorStyle,
  type TutorConversation,
  type TutorConversationDetail,
} from "@/features/tutor/schema/tutor.schema";

// conversationId omitted: the original stateless single-turn contract,
// unchanged. Passed: the answer persists into that thread and the
// response echoes the (possibly newly-created) conversation id back.
export async function askTutor(
  courseId: string,
  question: string,
  style: TutorStyle = "default",
  conversationId?: string
): Promise<TutorAskResult> {
  const data = await api<unknown>("/tutor/ask", {
    method: "POST",
    body: JSON.stringify({
      course_id: courseId,
      question,
      style,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
  });
  return tutorAskResultSchema.parse(data);
}

export async function createTutorConversation(
  courseId: string,
  skillId?: string
): Promise<TutorConversation> {
  const data = await api<unknown>("/tutor/conversations", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, skill_id: skillId ?? null }),
  });
  return tutorConversationSchema.parse(data);
}

export async function listTutorConversations(courseId: string): Promise<TutorConversation[]> {
  const data = await api<unknown>(`/tutor/conversations?course_id=${encodeURIComponent(courseId)}`);
  return tutorConversationListSchema.parse(data).conversations;
}

export async function fetchTutorConversation(conversationId: string): Promise<TutorConversationDetail> {
  const data = await api<unknown>(`/tutor/conversations/${conversationId}`);
  return tutorConversationDetailSchema.parse(data);
}

export async function deleteTutorConversation(conversationId: string): Promise<void> {
  await api<unknown>(`/tutor/conversations/${conversationId}`, { method: "DELETE" });
}
