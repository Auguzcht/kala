import { z } from "zod";
import { bankSkillStatusSchema } from "@/features/bank/schema/bank-status.schema";

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
  bankStatus: z.object({
    status: bankSkillStatusSchema,
    mcqReady: z.number().int().nonnegative(),
    mcqTarget: z.number().int().nonnegative(),
    usable: z.boolean(),
  }).optional(),
});

const practiceSetPayloadSchema = z.object({
  courseId: z.string(),
  setId: z.string().nullable(),
  items: z.array(practiceItemSchema),
});

const practiceBankStatusSchema = z.object({
  status: bankSkillStatusSchema,
  mcqReady: z.number().int().nonnegative(),
  mcqTarget: z.number().int().nonnegative(),
  usable: z.boolean(),
});

export const practiceSetProgressSchema = z.object({
  status: z.enum(["generating", "ready", "failed", "preparing", "no_material"]),
  requestedSize: z.number().int().nonnegative(),
  readyCount: z.number().int().nonnegative(),
  pendingCount: z.number().int().nonnegative(),
  failedCount: z.number().int().nonnegative(),
  failedOffsets: z.array(z.number().int().nonnegative()),
  bankStatus: practiceBankStatusSchema.optional(),
});

// A generated batch of items for one skill (POST /practice/{id}/set).
// `setId` is null and `items` empty when the course has no approved skill to
// generate against — the same degenerate case /next reports with item: null.
export const practiceSetSchema = practiceSetPayloadSchema
  .merge(practiceSetProgressSchema)
  // Async set responses include the resolved skill. The no-approved-skill
  // response is the one legitimate exception and omits it with setId null.
  .extend({
    includesRepeats: z.boolean().optional(),
    skillId: z.string().nullable().optional(),
    kind: z.literal("practice").optional(),
  });

// Per-student attempt metadata, shared by the set list and the set detail.
// Nulls (not missing) for a set this student has never attempted, so the UI
// branches on `attemptedCount === null`. Written only by the API's submit().
export const practiceSetAttemptSchema = z.object({
  attemptedCount: z.number().int().nullable(),
  correctCount: z.number().int().nullable(),
  lastAttemptedAt: z.string().nullable(),
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
export const practiceBridgeSetSchema = practiceSetPayloadSchema.extend({
  setId: z.string(),
});

// The retake list (GET /practice/{id}/sets), newest first.
export const practiceSetSummarySchema = z.object({
  setId: z.string(),
  skillId: z.string(),
  kind: z.string(),
  size: z.number().int().nonnegative(),
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
export type PracticeBankStatus = z.infer<typeof practiceBankStatusSchema>;
export type PracticeSavedSet = z.infer<typeof practiceSavedSetSchema>;
export type PracticeBridgeSet = z.infer<typeof practiceBridgeSetSchema>;
export type PracticeSetSummary = z.infer<typeof practiceSetSummarySchema>;
export type PracticeSetList = z.infer<typeof practiceSetListSchema>;
export type PracticeSetAttempt = z.infer<typeof practiceSetAttemptSchema>;
export type PracticeSubmitResult = z.infer<typeof practiceSubmitResultSchema>;
