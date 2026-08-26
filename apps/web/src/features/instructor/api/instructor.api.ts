import { api } from "@/lib/api/client";
import {
  atRiskSchema,
  heatmapSchema,
  proposedSkillsSchema,
  proposeSkillsResultSchema,
  reviewResponseSchema,
  studentTwinSchema,
  type AtRisk,
  type HeatmapData,
  type ProposedSkills,
  type ProposeSkillsResult,
  type ReviewResponse,
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

export async function fetchProposedSkills(courseId: string): Promise<ProposedSkills> {
  const data = await api<unknown>(`/dashboard/${courseId}/skills/proposed`);
  return proposedSkillsSchema.parse(data);
}

export async function reviewProposedSkill(
  courseId: string,
  skillId: string,
  decision: { status: "approved" | "rejected" }
): Promise<ReviewResponse> {
  const data = await api<unknown>(`/dashboard/${courseId}/skills/${skillId}/review`, {
    method: "PATCH",
    body: JSON.stringify(decision),
  });
  return reviewResponseSchema.parse(data);
}

export async function proposeSkills(courseId: string): Promise<ProposeSkillsResult> {
  const data = await api<unknown>(`/courses/${courseId}/skills/propose`, { method: "POST" });
  return proposeSkillsResultSchema.parse(data);
}
