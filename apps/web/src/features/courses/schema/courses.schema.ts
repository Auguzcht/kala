import { z } from "zod";

export const courseMetaSchema = z.object({
  id: z.string(),
  title: z.string(),
  lmsCourseId: z.string().nullable().optional(),
});

export type CourseMeta = z.infer<typeof courseMetaSchema>;
