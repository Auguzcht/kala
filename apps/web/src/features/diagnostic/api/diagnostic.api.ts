import { api } from "@/lib/api/client";
import {
  diagnosticSchema,
  diagnosticResultSchema,
  type Answer,
  type Diagnostic,
  type DiagnosticResult,
} from "@/features/diagnostic/schema/diagnostic.schema";

// Validate responses at the boundary with Zod. institutionId is derived
// from the session on the backend, never sent from the client.
export async function fetchDiagnostic(courseId: string): Promise<Diagnostic> {
  const data = await api<unknown>(`/courses/${courseId}/diagnostic`);
  return diagnosticSchema.parse(data);
}

export async function submitDiagnostic(
  courseId: string,
  answers: Answer[]
): Promise<DiagnosticResult> {
  const data = await api<unknown>(`/courses/${courseId}/diagnostic/submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
  return diagnosticResultSchema.parse(data);
}
