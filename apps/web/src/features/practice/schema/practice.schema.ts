import { z } from "zod";

export const practiceItemSchema = z.object({
  id: z.string(),
  skillId: z.string(),
  bloomLevel: z.string().nullable(),
  prompt: z.string(),
  choices: z.array(z.object({ id: z.string(), label: z.string() })),
});

export const practiceNextSchema = z.object({
  courseId: z.string(),
  item: practiceItemSchema.nullable(),
});

export const practiceSubmitResultSchema = z.object({
  correct: z.boolean(),
  explanation: z.string(),
  mastery: z.number().nullable(),
});

export type PracticeItem = z.infer<typeof practiceItemSchema>;
export type PracticeNext = z.infer<typeof practiceNextSchema>;
export type PracticeSubmitResult = z.infer<typeof practiceSubmitResultSchema>;
