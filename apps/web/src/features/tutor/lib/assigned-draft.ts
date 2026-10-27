import { z } from "zod";

const assignedTutorDraftSchema = z.object({
  id: z.string().uuid(),
  courseId: z.string().min(1),
  text: z.string().trim().min(1),
});

export type AssignedTutorDraft = z.infer<typeof assignedTutorDraftSchema>;

export function createAssignedTutorDraft(courseId: string, topic: string): AssignedTutorDraft {
  return assignedTutorDraftSchema.parse({
    id: crypto.randomUUID(),
    courseId,
    text: `Help me understand ${topic.trim()}. Explain the key ideas and guide me through an example.`,
  });
}

export function readAssignedTutorDraft(state: unknown, courseId: string): AssignedTutorDraft | null {
  const parsed = z.object({ assignedTutorDraft: assignedTutorDraftSchema }).safeParse(state);
  return parsed.success && parsed.data.assignedTutorDraft.courseId === courseId
    ? parsed.data.assignedTutorDraft
    : null;
}
