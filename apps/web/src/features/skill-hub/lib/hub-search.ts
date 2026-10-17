import { z } from "zod";

const optionalFlag = z.preprocess((value) => {
  if (value === "true" || value === "1" || value === 1) return true;
  if (value === "false" || value === "0" || value === 0) return false;
  return value;
}, z.boolean().optional()).catch(undefined);

export const hubSearchSchema = z.object({
  tab: z.enum(["lesson", "study", "test"]).optional().catch(undefined),
  setId: z.string().optional().catch(undefined),
  sessionId: z.string().optional().catch(undefined),
  attemptId: z.string().optional().catch(undefined),
  studySetId: z.string().optional().catch(undefined),
  missedItemIds: z.array(z.string()).optional().catch(undefined),
  repeats: optionalFlag,
  start: optionalFlag,
  mode: z.enum(["review", "all"]).optional().catch(undefined),
});
