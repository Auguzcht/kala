import { api } from "@/lib/api/client";
import { evidenceHistorySchema } from "@/features/twin/schema/evidence-history.schema";

export async function fetchEvidenceHistory(courseId: string, targetId: string | undefined, cursor: string | null) {
  const path = targetId
    ? `/dashboard/${encodeURIComponent(courseId)}/students/${encodeURIComponent(targetId)}/evidence`
    : `/courses/${encodeURIComponent(courseId)}/twin/evidence`;
  const query = new URLSearchParams({ limit: "25" });
  if (cursor !== null) query.set("cursor", cursor);
  return evidenceHistorySchema.parse(await api<unknown>(`${path}?${query}`));
}
