import { z } from "zod";

// Flashcard contract (study mode): a card is a FLIP, not an MCQ. The front
// shows the prompt, tapping reveals the back (answer label + explanation), and
// the student marks it themselves. There is no server grading and no choices
// in the payload — study is memorization, not assessment, and it does not
// move mastery (see services/api/app/routers/flashcards.py).
//
// The same generated item can be taken as a graded quiz separately; that is
// the /practice/{id}/set path (test mode), which is what feeds the twin.

export const flashcardBackSchema = z.object({
  label: z.string().nullable(),
  explanation: z.string(),
});

export const flashcardCardSchema = z.object({
  itemId: z.string(),
  skillId: z.string(),
  skillName: z.string().nullable().optional(),
  prompt: z.string(),
  back: flashcardBackSchema,
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

// POST /flashcards/{course_id}/review — self-marking one studied card.
// `remembered` is the student's own call; the server advances the schedule
// from it but does NOT grade and does NOT move mastery.
export const flashcardReviewResultSchema = z.object({
  remembered: z.boolean(),
  graduated: z.boolean(),
  dueInHours: z.number(),
  box: z.number(),
  reward: rewardSchema,
});

export type FlashcardBack = z.infer<typeof flashcardBackSchema>;
export type FlashcardCard = z.infer<typeof flashcardCardSchema>;
export type SrsStats = z.infer<typeof srsStatsSchema>;
export type Reward = z.infer<typeof rewardSchema>;
export type FlashcardDeck = z.infer<typeof flashcardDeckSchema>;
export type FlashcardReviewResult = z.infer<typeof flashcardReviewResultSchema>;
