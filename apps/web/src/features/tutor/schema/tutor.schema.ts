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

export const tutorConversationDetailSchema = tutorConversationSchema.extend({
  messages: z.array(tutorPersistedMessageSchema),
});

export const tutorConversationListSchema = z.object({
  conversations: z.array(tutorConversationSchema),
});

export type TutorStyle = z.infer<typeof tutorStyleSchema>;
export type TutorMessage = z.infer<typeof tutorMessageSchema>;
export type TutorAskResult = z.infer<typeof tutorAskResultSchema>;
export type TutorConversation = z.infer<typeof tutorConversationSchema>;
export type TutorPersistedMessage = z.infer<typeof tutorPersistedMessageSchema>;
export type TutorConversationDetail = z.infer<typeof tutorConversationDetailSchema>;
