import { z } from "zod";

export const tutorStyleSchema = z.enum(["default", "eli5", "detail"]);

// The follow-up chips (Hint / Explain) reuse the SAME grounded answer path;
// `style` only shifts the register of the framing (see routers/tutor.py).
export const tutorMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  text: z.string(),
});

// Stage 2 (AI overhaul): the tutor gained real, resumable conversations.
// `askTutor` (no conversation_id) keeps its original stateless contract —
// Lessons' Hint and Flashcards' Hint/Explain/Ask-a-friend all go through
// that path unchanged. Everything below is additive.
export const tutorAskResultSchema = z.object({
  answer: z.string(),
  conversationId: z.string().optional(),
});

export const tutorConversationSchema = z.object({
  id: z.string(),
  courseId: z.string(),
  skillId: z.string().nullable(),
  title: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const tutorPersistedMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  style: tutorStyleSchema.nullable(),
  createdAt: z.string(),
});

// Stage 4: private study-aid uploads, scoped to one conversation. Never
// part of the shared RAG corpus — see migration 0011's own comment for
// why. 'processing' is brief (extraction is synchronous on upload);
// 'failed' means the file is kept but contributes no context.
export const tutorAttachmentSchema = z.object({
  id: z.string(),
  filename: z.string(),
  mimeType: z.string(),
  sizeBytes: z.number(),
  status: z.enum(["processing", "ready", "failed"]),
  createdAt: z.string(),
});

export const tutorConversationDetailSchema = tutorConversationSchema.extend({
  messages: z.array(tutorPersistedMessageSchema),
  attachments: z.array(tutorAttachmentSchema).default([]),
});

export const tutorConversationListSchema = z.object({
  conversations: z.array(tutorConversationSchema),
});

export type TutorStyle = z.infer<typeof tutorStyleSchema>;
export type TutorMessage = z.infer<typeof tutorMessageSchema>;
export type TutorAskResult = z.infer<typeof tutorAskResultSchema>;
export type TutorConversation = z.infer<typeof tutorConversationSchema>;
export type TutorPersistedMessage = z.infer<typeof tutorPersistedMessageSchema>;
export type TutorAttachment = z.infer<typeof tutorAttachmentSchema>;
export type TutorConversationDetail = z.infer<typeof tutorConversationDetailSchema>;
