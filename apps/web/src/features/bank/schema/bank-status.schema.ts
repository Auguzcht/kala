import { z } from "zod";

export const bankSkillStatusSchema = z.enum([
  "waiting_content",
  "building",
  "ready",
  "no_material",
  "error",
]);

export const bankSkillStatusEntrySchema = z.object({
  skillId: z.string(),
  status: bankSkillStatusSchema,
  mcqReady: z.number().int().nonnegative(),
  mcqTarget: z.number().int().nonnegative(),
  depth: z.number().int().nonnegative(),
  usable: z.boolean(),
  lastError: z.string().nullable().optional(),
}).strict();

export const bankStatusSchema = z.object({
  courseId: z.string(),
  building: z.boolean(),
  skills: z.array(bankSkillStatusEntrySchema),
  bankServing: z.boolean(),
}).strict();

export type BankSkillStatus = z.infer<typeof bankSkillStatusSchema>;
export type BankSkillStatusEntry = z.infer<typeof bankSkillStatusEntrySchema>;
export type BankStatus = z.infer<typeof bankStatusSchema>;
