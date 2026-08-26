import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  detachAutoMatchedSkill,
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
