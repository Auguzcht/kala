import { z } from "zod";

export const tutorStyleSchema = z.enum(["default", "eli5", "detail"]);

// The follow-up chips (Hint / Explain) reuse the SAME grounded answer path;
// `style` only shifts the register of the framing (see routers/tutor.py).
export const tutorMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  text: z.string(),
});

export const tutorAskResultSchema = z.object({
  answer: z.string(),
});

export type TutorStyle = z.infer<typeof tutorStyleSchema>;
export type TutorMessage = z.infer<typeof tutorMessageSchema>;
export type TutorAskResult = z.infer<typeof tutorAskResultSchema>;
