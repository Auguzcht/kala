import { z } from "zod";

// What the learner's instructor has actually assigned them.
//
// The learner-facing half of the human-in-the-loop loop. The instructor
// surface generates AI recommendations and decides on each one; this is the
// only shape a decided action takes when it reaches the student.
//
// Note what is NOT in this schema: confidence, expected gain, the evidence
// panel, the model source, the decision note. Those are instructor-facing
// framing ABOUT the learner. Handing a student "the model is 84% confident
// you are weak at IAM" is exactly what the design brief rules out. They see
// the action and their teacher's note, nothing else.

export const planItemKindSchema = z.enum([
  "practice",
  "lesson",
  "flashcards",
  "tutor",
  "diagnostic",
  "outreach",
]);

export const planItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  kind: planItemKindSchema,
  priority: z.enum(["high", "medium", "low"]),
  status: z.enum(["approved", "modified", "completed"]),
  skillId: z.string().nullable(),
  skillName: z.string().nullable(),
  instructorNote: z.string().nullable(),
  assignedAt: z.string().nullable(),
});

export const planSchema = z.object({
  courseId: z.string(),
  plan: z.array(planItemSchema),
});

export type PlanItem = z.infer<typeof planItemSchema>;
export type PlanItemKind = z.infer<typeof planItemKindSchema>;
export type Plan = z.infer<typeof planSchema>;
