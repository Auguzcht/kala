import { z } from "zod";

// The session comes from the LTI launch, not a password login.
// The backend validates the launch and returns these claims.
export const sessionSchema = z.object({
  userId: z.string(),
  institutionId: z.string(), // tenant, resolved from LTI iss + deployment_id
  role: z.enum(["student", "instructor", "admin"]),
  courseId: z.string().optional(),
  displayName: z.string().optional(),
});

export type Session = z.infer<typeof sessionSchema>;
