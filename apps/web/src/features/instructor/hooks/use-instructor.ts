import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  RecommendationKind,
  RecommendationList,
} from "@/features/instructor/schema/instructor.schema";
import {
  createIntervention,
  decideRecommendation,
  detachAutoMatchedSkill,
  fetchCohortStats,
  fetchLearnerRecord,
  fetchRecommendations,
  fetchRoster,
  generateRecommendations,
  fetchAtRisk,
  fetchAutoMatchedSkills,
  fetchHeatmap,
  fetchProposedSkills,
  fetchStudentTwin,
  proposeSkills,
  reviewProposedSkill,
} from "@/features/instructor/api/instructor.api";

export function useHeatmap(courseId: string) {
  return useQuery({
    queryKey: ["heatmap", courseId],
    queryFn: () => fetchHeatmap(courseId),
  });
}

export function useAtRisk(courseId: string) {
  return useQuery({
    queryKey: ["at-risk", courseId],
    queryFn: () => fetchAtRisk(courseId),
  });
}

export function useStudentTwin(courseId: string, userId: string) {
  return useQuery({
    queryKey: ["student-twin", courseId, userId],
    queryFn: () => fetchStudentTwin(courseId, userId),
    enabled: !!userId,
  });
}

export function useProposedSkills(courseId: string) {
  return useQuery({
    queryKey: ["proposed-skills", courseId],
    queryFn: () => fetchProposedSkills(courseId),
  });
}

export function useReviewProposedSkill(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { skillId: string; status: "approved" | "rejected" }) =>
      reviewProposedSkill(courseId, args.skillId, { status: args.status }),
    onSuccess: () => {
      // Approving a skill changes what the cohort/heatmap can show.
      queryClient.invalidateQueries({ queryKey: ["proposed-skills", courseId] });
      queryClient.invalidateQueries({ queryKey: ["heatmap", courseId] });
    },
  });
}

export function useProposeSkills(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => proposeSkills(courseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proposed-skills", courseId] });
      // Auto-approved matches may have added live skills to the cohort.
      queryClient.invalidateQueries({ queryKey: ["heatmap", courseId] });
    },
  });
}

export function useAutoMatchedSkills(courseId: string) {
  return useQuery({
    queryKey: ["auto-matched-skills", courseId],
    queryFn: () => fetchAutoMatchedSkills(courseId),
  });
}

export function useDetachAutoMatchedSkill(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) => detachAutoMatchedSkill(courseId, skillId),
    onSuccess: () => {
      // The detached skill moves from auto-matched to the proposed list.
      queryClient.invalidateQueries({ queryKey: ["auto-matched-skills", courseId] });
      queryClient.invalidateQueries({ queryKey: ["proposed-skills", courseId] });
    },
  });
}

// ---- Cohort reads ---------------------------------------------------------

export function useRoster(courseId: string) {
  return useQuery({
    queryKey: ["roster", courseId],
    queryFn: () => fetchRoster(courseId),
    enabled: !!courseId,
  });
}

export function useCohortStats(courseId: string) {
  return useQuery({
    queryKey: ["cohort-stats", courseId],
    queryFn: () => fetchCohortStats(courseId),
    enabled: !!courseId,
  });
}

export function useLearnerRecord(courseId: string, userId: string) {
  return useQuery({
    queryKey: ["learner-record", courseId, userId],
    queryFn: () => fetchLearnerRecord(courseId, userId),
    enabled: !!courseId && !!userId,
  });
}

// ---- Recommendations (the teaching gate) ----------------------------------

export function useRecommendations(courseId: string, userId: string) {
  return useQuery({
    queryKey: ["recommendations", courseId, userId],
    queryFn: () => fetchRecommendations(courseId, userId),
    enabled: !!courseId && !!userId,
  });
}

export function useGenerateRecommendations(courseId: string, userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => generateRecommendations(courseId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", courseId, userId] });
      // The KPI strip carries the pending-decision count.
      queryClient.invalidateQueries({ queryKey: ["cohort-stats", courseId] });
    },
  });
}

export function useDecideRecommendation(courseId: string, userId: string) {
  const queryClient = useQueryClient();
  const key = ["recommendations", courseId, userId];
  return useMutation({
    mutationFn: (args: {
      recId: string;
      status: "approved" | "modified" | "rejected";
      title?: string;
      kind?: RecommendationKind;
      priority?: "high" | "medium" | "low";
      decisionNote?: string;
      instructorNote?: string;
    }) =>
      decideRecommendation(courseId, args.recId, {
        status: args.status,
        title: args.title,
        kind: args.kind,
        priority: args.priority,
        decision_note: args.decisionNote,
        instructor_note: args.instructorNote,
      }),
    // Optimistic on purpose. A decision is the one interaction in this
    // product where latency reads as doubt: a teacher clicks Approve and
    // watches a card sit there. Moving the card to the decision history
    // immediately, then reconciling with the server response, makes the
    // gate feel like a decision rather than a form submission. Rolled back
    // on error, and the toast in DecisionCenter reports the failure.
    onMutate: async (args) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<RecommendationList>(key);
      if (previous) {
        queryClient.setQueryData<RecommendationList>(key, {
          ...previous,
          recommendations: previous.recommendations.map((r) =>
            r.id === args.recId
              ? {
                  ...r,
                  status: args.status,
                  title: args.title ?? r.title,
                  kind: args.kind ?? r.kind,
                  priority: args.priority ?? r.priority,
                  decisionNote: args.decisionNote ?? r.decisionNote,
                  instructorNote: args.instructorNote ?? r.instructorNote,
                  decidedAt: new Date().toISOString(),
                }
              : r
          ),
        });
      }
      return { previous };
    },
    onError: (_err, _args, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: key });
      queryClient.invalidateQueries({ queryKey: ["cohort-stats", courseId] });
    },
  });
}

export function useCreateIntervention(courseId: string, userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      title: string;
      kind: RecommendationKind;
      priority?: "high" | "medium" | "low";
      skillId?: string | null;
      instructorNote?: string;
    }) =>
      createIntervention(courseId, userId, {
        title: args.title,
        kind: args.kind,
        priority: args.priority,
        skill_id: args.skillId ?? null,
        instructor_note: args.instructorNote,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", courseId, userId] });
      queryClient.invalidateQueries({ queryKey: ["cohort-stats", courseId] });
    },
  });
}
