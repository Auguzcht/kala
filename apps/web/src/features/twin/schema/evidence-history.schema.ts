import { z } from "zod";
import { evidenceEventSchema } from "@/features/twin/schema/twin.schema";

export const evidenceHistorySchema = z.object({
  courseId: z.string(),
  evidence: z.array(evidenceEventSchema),
  nextCursor: z.string().nullable().optional(),
});
export type EvidenceHistory = z.infer<typeof evidenceHistorySchema>;
