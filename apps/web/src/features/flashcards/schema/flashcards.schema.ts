import { z } from "zod";

// Flashcard contract (Learn Loop v2): the deck is SRS-scheduled MCQs, not
// self-reported Q&A flips. Answer keys never leave the server — grading and
// reveal both happen through the API, never by trusting the client.
// Source of truth: services/api/app/routers/flashcards.py.

export const flashcardChoiceSchema = z.object({
  id: z.string(),
  label: z.string(),
});

export const flashcardCardSchema = z.object({
  itemId: z.string(),
  skillId: z.string(),
  skillName: z.string().nullable().optional(),
  prompt: z.string(),
  choices: z.array(flashcardChoiceSchema),
  state: z.enum(["due", "new"]),
  box: z.number(),
});

export const srsStatsSchema = z.object({
  tracked: z.number(),
  due: z.number(),
  learning: z.number(),
  mastered: z.number(),
});

export const rewardSchema = z.object({
  xp: z.number(),
  attempts: z.number(),
  correct: z.number(),
  streakDays: z.number(),
  badges: z.array(
    z.object({ kind: z.string(), label: z.string(), tier: z.string() })
  ),
});

export const flashcardDeckSchema = z.object({
  courseId: z.string(),
  cards: z.array(flashcardCardSchema),
  stats: srsStatsSchema,
});

// POST /flashcards/{course_id}/review — grading a committed choice.
export const flashcardReviewResultSchema = z.object({
  correct: z.boolean(),
  explanation: z.string(),
  graduated: z.boolean(),
  dueInHours: z.number(),
  box: z.number(),
  mastery: z.number().nullable(),
  reward: rewardSchema,
});

// POST /flashcards/{course_id}/reveal — pre-commit Show Answer. The reveal is
// committed as a lapse server-side BEFORE the answer returns, so the client
// treats a revealed card as terminal: never call review for the same item.
export const flashcardRevealResultSchema = z.object({
  revealed: z.literal(true),
  correctChoiceId: z.string(),
  correctLabel: z.string().nullable(),
  explanation: z.string(),
  dueInHours: z.number(),
  box: z.number(),
  mastery: z.number().nullable(),
  reward: rewardSchema,
});

export type FlashcardChoice = z.infer<typeof flashcardChoiceSchema>;
export type FlashcardCard = z.infer<typeof flashcardCardSchema>;
export type SrsStats = z.infer<typeof srsStatsSchema>;
export type Reward = z.infer<typeof rewardSchema>;
export type FlashcardDeck = z.infer<typeof flashcardDeckSchema>;
export type FlashcardReviewResult = z.infer<typeof flashcardReviewResultSchema>;
export type FlashcardRevealResult = z.infer<typeof flashcardRevealResultSchema>;
