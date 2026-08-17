import { z } from "zod";

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

export const answerSchema = z.object({
  questionId: z.string(),
  choiceId: z.string(),
  latencyMs: z.number().int().nonnegative(),
});

export const diagnosticResultSchema = z.object({
  correctCount: z.number().int(),
  total: z.number().int(),
});

export type Question = z.infer<typeof questionSchema>;
export type Diagnostic = z.infer<typeof diagnosticSchema>;
export type Answer = z.infer<typeof answerSchema>;
export type DiagnosticResult = z.infer<typeof diagnosticResultSchema>;
