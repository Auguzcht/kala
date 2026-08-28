import { z } from "zod";

// Reward view (Learn Loop v2): XP, streak, and badges are DERIVED from the
// evidence log + mastery state — there is no writable balance, so the client
// can never inflate these. Source of truth: services/api/app/learn/xp.py +
// routers/gamification.py.

export const gamificationBadgeSchema = z.object({
  kind: z.string(),
  label: z.string(),
  tier: z.string(),
});

export const gamificationSummarySchema = z.object({
  xp: z.number(),
  attempts: z.number(),
  correct: z.number(),
  streakDays: z.number(),
  badges: z.array(gamificationBadgeSchema),
});

export type GamificationBadge = z.infer<typeof gamificationBadgeSchema>;
export type GamificationSummary = z.infer<typeof gamificationSummarySchema>;
