import { api } from "@/lib/api/client";
import {
  diagnosticSchema,
  diagnosticStatusSchema,
  diagnosticResultSchema,
  type Answer,
  type Diagnostic,
  type DiagnosticStatus,
  type DiagnosticResult,
} from "@/features/diagnostic/schema/diagnostic.schema";

// Validate responses at the boundary with Zod. institutionId is derived
// from the session on the backend, never sent from the client.
export async function fetchDiagnostic(courseId: string): Promise<Diagnostic> {
  const data = await api<unknown>(`/courses/${courseId}/diagnostic`);
  return diagnosticSchema.parse(data);
}

// No generation involved, safe to poll cheaply for a nav badge.
export async function fetchDiagnosticStatus(courseId: string): Promise<DiagnosticStatus> {
  const data = await api<unknown>(`/courses/${courseId}/diagnostic/status`);
  return diagnosticStatusSchema.parse(data);
}

export async function submitDiagnostic(
  courseId: string,
  answers: Answer[]
): Promise<DiagnosticResult> {
  const data = await api<unknown>(`/courses/${courseId}/diagnostic/submit`, {
    method: "POST",
    body: JSON.stringify({
      answers: answers.map((a) => ({
        item_id: a.itemId,
        choice_id: a.choiceId,
        latency_ms: a.latencyMs,
      })),
    }),
  });
  return diagnosticResultSchema.parse(data);
}
