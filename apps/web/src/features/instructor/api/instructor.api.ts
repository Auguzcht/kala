import { api } from "@/lib/api/client";
import {
  atRiskSchema,
  heatmapSchema,
  studentTwinSchema,
  type AtRisk,
  type HeatmapData,
  type StudentTwin,
} from "@/features/instructor/schema/instructor.schema";

export async function fetchHeatmap(courseId: string): Promise<HeatmapData> {
  const data = await api<unknown>(`/dashboard/${courseId}/heatmap`);
  return heatmapSchema.parse(data);
}

export async function fetchAtRisk(courseId: string): Promise<AtRisk> {
  const data = await api<unknown>(`/dashboard/${courseId}/at-risk`);
  return atRiskSchema.parse(data);
}

export async function fetchStudentTwin(courseId: string, userId: string): Promise<StudentTwin> {
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/twin`);
  return studentTwinSchema.parse(data);
}
