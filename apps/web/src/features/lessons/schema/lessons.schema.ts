import { z } from "zod";

// Guided lesson contract (Learn Loop v2): a persistent, generated-once
// walkthrough per (course, skill). Each step is an explain-then-check unit;
// the check is a server-graded MCQ whose answer key never leaves the API.
// Source of truth: services/api/app/learn/lessons.py + routers/lessons.py.

const lessonChoiceSchema = z.object({
  id: z.string(),
  label: z.string(),
});

export const lessonCheckSchema = z.object({
  itemId: z.string(),
  prompt: z.string(),
  choices: z.array(lessonChoiceSchema),
});

export const lessonStepSchema = z.object({
  id: z.string(),
  position: z.number(),
  summary: z.string(),
  detailPoints: z.array(z.string()),
  misconception: z.string().nullable(),
  keyTakeaway: z.string().nullable(),
  bloomLevel: z.string().nullable(),
  // A pure-explanation step has no check; the step still advances visually.
  check: lessonCheckSchema.nullable(),
});

export const lessonSchema = z.object({
  lessonId: z.string(),
  skillId: z.string(),
  moduleRef: z.string().nullable(),
  title: z.string(),
  status: z.enum(["generating", "ready", "failed"]),
  steps: z.array(lessonStepSchema),
});

export const lessonRewardSchema = z.object({
  xp: z.number(),
  attempts: z.number(),
  correct: z.number(),
  streakDays: z.number(),
  badges: z.array(
    z.object({ kind: z.string(), label: z.string(), tier: z.string() })
  ),
});

export const lessonCheckResultSchema = z.object({
  correct: z.boolean(),
  explanation: z.string(),
  advance: z.boolean(),
  mastery: z.number().nullable(),
  reward: lessonRewardSchema,
});

export type LessonChoice = z.infer<typeof lessonChoiceSchema>;
export type LessonCheck = z.infer<typeof lessonCheckSchema>;
export type LessonStep = z.infer<typeof lessonStepSchema>;
export type Lesson = z.infer<typeof lessonSchema>;
export type LessonReward = z.infer<typeof lessonRewardSchema>;
export type LessonCheckResult = z.infer<typeof lessonCheckResultSchema>;
