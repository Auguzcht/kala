import type { DiagnosticStatus } from "@/features/diagnostic/schema/diagnostic.schema";

/** New actionable counts take precedence; old responses retain their due flag. */
export function isDiagnosticDue(status: DiagnosticStatus | undefined): boolean {
  return status?.dueSkillCount !== undefined ? status.dueSkillCount > 0 : status?.due ?? false;
}
