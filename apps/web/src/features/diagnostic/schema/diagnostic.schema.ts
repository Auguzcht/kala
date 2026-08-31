import { z } from "zod";
import { masteryBandSchema } from "@/features/twin/schema/twin.schema";

export const questionSchema = z.object({
  id: z.string(),
  skillId: z.string(),
  bloomLevel: z.enum([
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
  ]),
  prompt: z.string(),
  choices: z.array(z.object({ id: z.string(), label: z.string() })),
});

export const diagnosticSchema = z.object({
  courseId: z.string(),
  questions: z.array(questionSchema),
});

// itemId + choiceId only. The backend never trusts the client to say
// whether an answer was correct, it looks the item back up and grades it.
export const answerSchema = z.object({
  itemId: z.string(),
  choiceId: z.string(),
  latencyMs: z.number().int().nonnegative(),
});

export const answerResultSchema = z.object({
  itemId: z.string(),
  correct: z.boolean(),
  explanation: z.string(),
});

// One row per skill the diagnostic touched. priorEstimate/priorBand are
// null for a skill with no earlier evidence (the diagnostic is usually the
// FIRST evidence for every skill, so "no-evidence -> developing/proficient"
// is the common case, not the exception) — the backend already makes this
// distinction (see routers/diagnostic.py's submit_diagnostic), never
// collapses it to a 0.0.
export const masteryDeltaSchema = z.object({
  skillId: z.string(),
  skillName: z.string(),
  priorEstimate: z.number().nullable(),
  priorBand: masteryBandSchema,
  posteriorEstimate: z.number(),
  posteriorBand: masteryBandSchema,
});

export const diagnosticResultSchema = z.object({
  correctCount: z.number().int(),
  total: z.number().int(),
  results: z.array(answerResultSchema),
  masteryDelta: z.array(masteryDeltaSchema),
});

export type Question = z.infer<typeof questionSchema>;
export type Diagnostic = z.infer<typeof diagnosticSchema>;
export type Answer = z.infer<typeof answerSchema>;
export type AnswerResult = z.infer<typeof answerResultSchema>;
export type MasteryDelta = z.infer<typeof masteryDeltaSchema>;
export type DiagnosticResult = z.infer<typeof diagnosticResultSchema>;
