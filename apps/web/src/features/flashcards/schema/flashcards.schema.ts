import { z } from "zod";
import { bankSkillStatusSchema } from "@/features/bank/schema/bank-status.schema";

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
  skillName: z.string().nullable(),
  prompt: z.string(),
  back: flashcardBackSchema,
  state: z.enum(["due", "new", "learning", "slipping", "known"]),
  box: z.number(),
});

export const flashcardMemoryStateSchema = z.enum(["new", "learning", "slipping", "known", "due"]);

export const flashcardMembershipCardSchema = z.object({
  itemId: z.string(),
  prompt: z.string(),
  back: flashcardBackSchema,
  state: flashcardMemoryStateSchema,
  due: z.boolean(),
  dueAt: z.string().nullable(),
});

export const flashcardMembershipCountsSchema = z.object({
  new: z.number().int().nonnegative(),
  learning: z.number().int().nonnegative(),
  slipping: z.number().int().nonnegative(),
  known: z.number().int().nonnegative(),
  dueToday: z.number().int().nonnegative(),
});

export const flashcardMembershipSchema = z.object({
  skillId: z.string(),
  counts: flashcardMembershipCountsSchema,
  cards: z.array(flashcardMembershipCardSchema),
});

export const srsStatsSchema = z.object({
  tracked: z.number().int().nonnegative(),
  due: z.number().int().nonnegative(),
  learning: z.number().int().nonnegative(),
  mastered: z.number().int().nonnegative(),
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

const flashcardBankStatusSchema = z.object({
  status: bankSkillStatusSchema,
  mcqReady: z.number().int().nonnegative(),
});

export const flashcardDeckSchema = z.object({
  courseId: z.string(),
  cards: z.array(flashcardCardSchema),
  stats: srsStatsSchema,
  bankStatus: flashcardBankStatusSchema.optional(),
  mode: z.enum(["review", "all"]).optional(),
  sessionId: z.string().optional(),
  offset: z.number().int().nonnegative().optional(),
  limit: z.number().int().positive().optional(),
  totalCards: z.number().int().nonnegative().optional(),
  hasMore: z.boolean().optional(),
  newRemainingToday: z.number().int().nonnegative().optional(),
  // Compatibility with the Phase 4 response name before it was standardized.
  newCardsRemainingToday: z.number().int().nonnegative().optional(),
});

// POST /flashcards/{course_id}/review — self-marking one studied card.
// `remembered` is the student's own call; the server advances the schedule
// from it but does NOT grade and does NOT move mastery.
export const flashcardReviewResultSchema = z.object({
  remembered: z.boolean(),
  graduated: z.boolean(),
  dueInHours: z.number(),
  dueAt: z.string().nullable().optional(),
  box: z.number(),
  reward: rewardSchema,
});

export type FlashcardBack = z.infer<typeof flashcardBackSchema>;
export type FlashcardCard = z.infer<typeof flashcardCardSchema>;
export type FlashcardMembershipCard = z.infer<typeof flashcardMembershipCardSchema>;
export type FlashcardMembership = z.infer<typeof flashcardMembershipSchema> & {
  /** True only when the membership endpoint is unavailable and the legacy
   * review deck was used as a safe fallback. */
  isFallback?: boolean;
  fallbackTracked?: number;
};
export type SrsStats = z.infer<typeof srsStatsSchema>;
export type Reward = z.infer<typeof rewardSchema>;
export type FlashcardDeck = z.infer<typeof flashcardDeckSchema>;
export type FlashcardReviewResult = z.infer<typeof flashcardReviewResultSchema>;
