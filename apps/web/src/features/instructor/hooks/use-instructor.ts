import { useQuery } from "@tanstack/react-query";
import {
  fetchAtRisk,
  fetchHeatmap,
  fetchStudentTwin,
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
