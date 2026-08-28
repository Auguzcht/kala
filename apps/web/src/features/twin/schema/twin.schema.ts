import { z } from "zod";

// Mastery bands are neutral-to-gold. Red never enters this scale; it
// belongs to the at-risk axis (instructor surface, a different object).
export const masteryBandSchema = z.enum(["no-evidence", "developing", "proficient", "mastered"]);

export const twinSkillSchema = z.object({
  skillId: z.string(),
  name: z.string(),
  bloomLevel: z.string().nullable().optional(),
  moduleRef: z.string().nullable().optional(),
  estimate: z.number().nullable(),
  attempts: z.number(),
  band: masteryBandSchema,
});

export const evidenceEventSchema = z.object({
  id: z.string(),
  type: z.string(),
  correct: z.boolean().nullable(),
  latencyMs: z.number().nullable().optional(),
  skillName: z.string(),
  createdAt: z.string().nullable().optional(),
});

export const twinSchema = z.object({
  courseId: z.string(),
  readiness: z.number().nullable(),
  skills: z.array(twinSkillSchema),
  evidence: z.array(evidenceEventSchema),
});

export const nextUpSchema = z.object({
  courseId: z.string(),
  next: z
    .object({
      skillId: z.string(),
      skillName: z.string(),
      bloomLevel: z.string().nullable().optional(),
      kind: z.string(),
      reason: z.string(),
      estimate: z.number().nullable(),
    })
    .nullable(),
});

export type MasteryBand = z.infer<typeof masteryBandSchema>;
export type TwinSkill = z.infer<typeof twinSkillSchema>;
export type EvidenceEvent = z.infer<typeof evidenceEventSchema>;
export type Twin = z.infer<typeof twinSchema>;
export type NextUp = z.infer<typeof nextUpSchema>;
export type NextUpRecommendation = NonNullable<NextUp["next"]>;
