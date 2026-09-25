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

const practiceSetPayloadSchema = z.object({
  courseId: z.string(),
  setId: z.string().nullable(),
  items: z.array(practiceItemSchema),
});

export const practiceSetProgressSchema = z.object({
  status: z.enum(["generating", "ready", "failed"]),
  requestedSize: z.number().int().nonnegative(),
  readyCount: z.number().int().nonnegative(),
  pendingCount: z.number().int().nonnegative(),
  failedCount: z.number().int().nonnegative(),
  failedOffsets: z.array(z.number().int().nonnegative()),
});

// A generated batch of items for one skill (POST /practice/{id}/set).
// `setId` is null and `items` empty when the course has no approved skill to
// generate against — the same degenerate case /next reports with item: null.
export const practiceSetSchema = practiceSetPayloadSchema
  .merge(practiceSetProgressSchema)
  // Async set responses include the resolved skill. The no-approved-skill
  // response is the one legitimate exception and omits it with setId null.
  .extend({ skillId: z.string().nullable().optional() });

// Per-student attempt metadata, shared by the set list and the set detail.
// Nulls (not missing) for a set this student has never attempted, so the UI
// branches on `attemptedCount === null`. Written only by the API's submit().
// `.nullable().default(null)` also tolerates an older API that predates the
// field entirely — an absent attempt count means the same thing to the UI as
// a null one (never attempted), so a deployment-order gap can't hard-fail the
// whole set list on a Zod parse.
export const practiceSetAttemptSchema = z.object({
  attemptedCount: z.number().nullable().default(null),
  correctCount: z.number().nullable().default(null),
  lastAttemptedAt: z.string().nullable().default(null),
});

// A saved set loaded by id (GET /practice/{id}/sets/{set_id}) — used to
// re-enter test mode on a set the student already has (the bridge handoff and
// the retake list). Carries prompts + choices only; the answer key stays
// server-side (it is a graded test, not a flashcard browse).
export const practiceSavedSetSchema = z.object({
  courseId: z.string(),
  setId: z.string(),
  skillId: z.string(),
  kind: z.string(),
  items: z.array(practiceItemSchema),
}).merge(practiceSetProgressSchema).merge(practiceSetAttemptSchema);

// The study-to-test bridge intentionally remains its old synchronous
// contract; it does not touch item_generation_jobs.
export const practiceBridgeSetSchema = practiceSetPayloadSchema;

// The retake list (GET /practice/{id}/sets), newest first.
export const practiceSetSummarySchema = z.object({
  setId: z.string(),
  skillId: z.string(),
  kind: z.string(),
  size: z.number(),
  createdAt: z.string(),
}).merge(practiceSetAttemptSchema);

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
export type PracticeBridgeSet = z.infer<typeof practiceBridgeSetSchema>;
export type PracticeSetSummary = z.infer<typeof practiceSetSummarySchema>;
export type PracticeSetList = z.infer<typeof practiceSetListSchema>;
export type PracticeSetAttempt = z.infer<typeof practiceSetAttemptSchema>;
export type PracticeSubmitResult = z.infer<typeof practiceSubmitResultSchema>;
