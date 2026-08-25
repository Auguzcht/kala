import { z } from "zod";

export const tutorMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  text: z.string(),
});

export const tutorAskResultSchema = z.object({
  answer: z.string(),
});

export type TutorMessage = z.infer<typeof tutorMessageSchema>;
export type TutorAskResult = z.infer<typeof tutorAskResultSchema>;
