import { api } from "@/lib/api/client";
import {
  atRiskSchema,
  autoMatchedSkillsSchema,
  detachResponseSchema,
  heatmapSchema,
  proposedSkillsSchema,
  proposeSkillsResultSchema,
  reviewResponseSchema,
  studentTwinSchema,
  type AtRisk,
  type AutoMatchedSkills,
  type DetachResponse,
  type HeatmapData,
  type ProposedSkills,
  type ProposeSkillsResult,
  type ReviewResponse,
  type StudentTwin,
  cohortStatsSchema,
  generateRecommendationsSchema,
  learnerRecordSchema,
  recommendationListSchema,
  recommendationSchema,
  rosterSchema,
  type CohortStats,
  type GenerateRecommendations,
  type LearnerRecord,
  type Recommendation,
  type RecommendationKind,
  type RecommendationList,
  type Roster,
} from "@/features/instructor/schema/instructor.schema";

export async function fetchHeatmap(courseId: string, timeoutMs?: number): Promise<HeatmapData> {
  const data = await api<unknown>(`/dashboard/${courseId}/heatmap`, undefined, timeoutMs);
  return heatmapSchema.parse(data);
}

export async function fetchAtRisk(courseId: string, timeoutMs?: number): Promise<AtRisk> {
  const data = await api<unknown>(`/dashboard/${courseId}/at-risk`, undefined, timeoutMs);
  return atRiskSchema.parse(data);
}

export async function fetchStudentTwin(courseId: string, userId: string): Promise<StudentTwin> {
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/twin`);
  return studentTwinSchema.parse(data);
}

export async function fetchProposedSkills(courseId: string, timeoutMs?: number): Promise<ProposedSkills> {
  const data = await api<unknown>(`/dashboard/${courseId}/skills/proposed`, undefined, timeoutMs);
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

export async function fetchAutoMatchedSkills(courseId: string, timeoutMs?: number): Promise<AutoMatchedSkills> {
  const data = await api<unknown>(`/dashboard/${courseId}/skills/auto-matched`, undefined, timeoutMs);
  return autoMatchedSkillsSchema.parse(data);
}

export async function detachAutoMatchedSkill(
  courseId: string,
  skillId: string
): Promise<DetachResponse> {
  const data = await api<unknown>(`/dashboard/${courseId}/skills/${skillId}/detach`, {
    method: "PATCH",
  });
  return detachResponseSchema.parse(data);
}

// ---- Cohort reads ---------------------------------------------------------

export async function fetchRoster(courseId: string, timeoutMs?: number): Promise<Roster> {
  const data = await api<unknown>(`/dashboard/${courseId}/roster`, undefined, timeoutMs);
  return rosterSchema.parse(data);
}

export async function fetchCohortStats(courseId: string, timeoutMs?: number): Promise<CohortStats> {
  const data = await api<unknown>(`/dashboard/${courseId}/stats`, undefined, timeoutMs);
  return cohortStatsSchema.parse(data);
}

export async function fetchLearnerRecord(courseId: string, userId: string): Promise<LearnerRecord> {
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/record`);
  return learnerRecordSchema.parse(data);
}

// ---- Recommendations (the teaching gate) ----------------------------------

export async function fetchRecommendations(
  courseId: string,
  userId: string
): Promise<RecommendationList> {
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/recommendations`);
  return recommendationListSchema.parse(data);
}

export async function generateRecommendations(
  courseId: string,
  userId: string
): Promise<GenerateRecommendations> {
  // Model call: no timeout, same as the other generative paths in the app.
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/recommendations`, {
    method: "POST",
  });
  return generateRecommendationsSchema.parse(data);
}

export async function decideRecommendation(
  courseId: string,
  recId: string,
  decision: {
    status: "approved" | "modified" | "rejected";
    title?: string;
    kind?: RecommendationKind;
    priority?: "high" | "medium" | "low";
    decision_note?: string;
    instructor_note?: string;
  }
): Promise<Recommendation> {
  const data = await api<unknown>(`/dashboard/${courseId}/recommendations/${recId}`, {
    method: "PATCH",
    body: JSON.stringify(decision),
  });
  return recommendationSchema.parse(data);
}

export async function createIntervention(
  courseId: string,
  userId: string,
  body: {
    title: string;
    kind: RecommendationKind;
    priority?: "high" | "medium" | "low";
    skill_id?: string | null;
    instructor_note?: string;
  }
): Promise<Recommendation> {
  const data = await api<unknown>(`/dashboard/${courseId}/students/${userId}/interventions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return recommendationSchema.parse(data);
}
