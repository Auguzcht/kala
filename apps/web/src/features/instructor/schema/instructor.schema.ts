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

export type HeatmapSkill = z.infer<typeof heatmapSkillSchema>;
export type HeatmapStudent = z.infer<typeof heatmapStudentSchema>;
export type HeatmapCell = z.infer<typeof heatmapCellSchema>;
export type HeatmapData = z.infer<typeof heatmapSchema>;
export type AtRiskFlag = z.infer<typeof atRiskFlagSchema>;
export type AtRisk = z.infer<typeof atRiskSchema>;
export type StudentTwin = z.infer<typeof studentTwinSchema>;
