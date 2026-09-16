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

// A generated batch of items for one skill (POST /practice/{id}/set).
// `setId` is null and `items` empty when the course has no approved skill to
// generate against — the same degenerate case /next reports with item: null.
export const practiceSetSchema = z.object({
  courseId: z.string(),
  setId: z.string().nullable(),
  items: z.array(practiceItemSchema),
});

export const practiceSubmitResultSchema = z.object({
  correct: z.boolean(),
  explanation: z.string(),
  mastery: z.number().nullable(),
});

export type PracticeItem = z.infer<typeof practiceItemSchema>;
export type PracticeNext = z.infer<typeof practiceNextSchema>;
export type PracticeSet = z.infer<typeof practiceSetSchema>;
export type PracticeSubmitResult = z.infer<typeof practiceSubmitResultSchema>;
