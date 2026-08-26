import { z } from "zod";
import { masteryBandSchema, twinSchema } from "@/features/twin/schema/twin.schema";

export const heatmapSkillSchema = z.object({
  skillId: z.string(),
  name: z.string(),
  bloomLevel: z.string().nullable().optional(),
  cohortBand: masteryBandSchema,
  cohortEstimate: z.number().nullable(),
});

export const heatmapStudentSchema = z.object({
  userId: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
});

export const heatmapCellSchema = z.object({
  userId: z.string(),
  skillId: z.string(),
  estimate: z.number().nullable(),
  attempts: z.number(),
  band: masteryBandSchema,
});

export const heatmapSchema = z.object({
  courseId: z.string(),
  cohortReadiness: z.number().nullable(),
  skills: z.array(heatmapSkillSchema),
  students: z.array(heatmapStudentSchema),
  cells: z.array(heatmapCellSchema),
});

export const atRiskFlagSchema = z.object({
  userId: z.string(),
  pseudonym: z.string(),
  initials: z.string(),
  reason: z.string(),
  daysInactive: z.number().nullable(),
  evidenceCount: z.number(),
  weakestSkillNames: z.array(z.string()),
});

export const atRiskSchema = z.object({
  courseId: z.string(),
  flags: z.array(atRiskFlagSchema),
});

// Instructor's read of one student's twin: the twin shape + pseudonym.
export const studentTwinSchema = twinSchema.extend({ pseudonym: z.string() });

// HITL skill proposals awaiting review (docs/SKILL_PIPELINE.md). Rows come
// back snake_case from the review endpoint (DB-shaped, not generated types).
export const proposedSkillSchema = z.object({
  id: z.string(),
  name: z.string(),
  bloom_level: z.string(),
  blueprint_weight: z.number(),
  proposed_source: z.string().nullable(),
});

export const proposedSkillsSchema = z.object({
  courseId: z.string(),
  proposed: z.array(proposedSkillSchema),
});

export const reviewResponseSchema = z.object({
  skillId: z.string(),
  status: z.enum(["approved", "rejected"]),
});

// On-demand proposal trigger (POST /courses/{id}/skills/propose). Skipped
// shape when the course already has skills; full shape when it ran.
export const proposeSkillsResultSchema = z.object({
  skipped: z.boolean(),
  reason: z.string().optional(),
  modulesProcessed: z.number().optional(),
  proposed: z.number().optional(),
  auto_approved: z.number().optional(),
  flagged_possible_duplicate: z.number().optional(),
});

export type HeatmapSkill = z.infer<typeof heatmapSkillSchema>;
export type HeatmapStudent = z.infer<typeof heatmapStudentSchema>;
export type HeatmapCell = z.infer<typeof heatmapCellSchema>;
export type HeatmapData = z.infer<typeof heatmapSchema>;
export type AtRiskFlag = z.infer<typeof atRiskFlagSchema>;
export type AtRisk = z.infer<typeof atRiskSchema>;
export type StudentTwin = z.infer<typeof studentTwinSchema>;
export type ProposedSkill = z.infer<typeof proposedSkillSchema>;
export type ProposedSkills = z.infer<typeof proposedSkillsSchema>;
export type ReviewResponse = z.infer<typeof reviewResponseSchema>;
export type ProposeSkillsResult = z.infer<typeof proposeSkillsResultSchema>;
