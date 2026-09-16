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

// A saved set loaded by id (GET /practice/{id}/sets/{set_id}) — used to
// re-enter test mode on a set the student already has (the bridge handoff and
// the retake list).
export const practiceSavedSetSchema = z.object({
  courseId: z.string(),
  setId: z.string(),
  skillId: z.string(),
  kind: z.string(),
  items: z.array(practiceItemSchema),
});

// The retake list (GET /practice/{id}/sets), newest first.
export const practiceSetSummarySchema = z.object({
  setId: z.string(),
  skillId: z.string(),
  kind: z.string(),
  size: z.number(),
  createdAt: z.string(),
});

export const practiceSetListSchema = z.object({
  courseId: z.string(),
  sets: z.array(practiceSetSummarySchema),
});

export const practiceSubmitResultSchema = z.object({
  correct: z.boolean(),
  explanation: z.string(),
  mastery: z.number().nullable(),
});

export type PracticeItem = z.infer<typeof practiceItemSchema>;
export type PracticeNext = z.infer<typeof practiceNextSchema>;
export type PracticeSet = z.infer<typeof practiceSetSchema>;
export type PracticeSavedSet = z.infer<typeof practiceSavedSetSchema>;
export type PracticeSetSummary = z.infer<typeof practiceSetSummarySchema>;
export type PracticeSetList = z.infer<typeof practiceSetListSchema>;
export type PracticeSubmitResult = z.infer<typeof practiceSubmitResultSchema>;
