import { api } from "@/lib/api/client";
import {
  tutorAskResultSchema,
  tutorConversationSchema,
  tutorConversationDetailSchema,
  tutorConversationListSchema,
  tutorAttachmentSchema,
  type TutorAskResult,
  type TutorStyle,
  type TutorConversation,
  type TutorConversationDetail,
  type TutorAttachment,
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

// Stage 4: private study-aid uploads, scoped to one conversation. Uses
// FormData, not JSON — the shared api() client detects that and skips
// its default Content-Type so the browser's own multipart boundary
// survives (see lib/api/client.ts).
export async function uploadTutorAttachment(
  conversationId: string,
  file: File
): Promise<TutorAttachment> {
  const form = new FormData();
  form.append("file", file);
  const data = await api<unknown>(`/tutor/conversations/${conversationId}/attachments`, {
    method: "POST",
    body: form,
  });
  return tutorAttachmentSchema.parse(data);
}

export async function deleteTutorAttachment(
  conversationId: string,
  attachmentId: string
): Promise<void> {
  await api<unknown>(`/tutor/conversations/${conversationId}/attachments/${attachmentId}`, {
    method: "DELETE",
  });
}
