import { useQuery } from "@tanstack/react-query";
import { fetchCourse } from "@/features/courses/api/courses.api";

export function useCourse(courseId: string) {
  return useQuery({
    queryKey: ["course", courseId],
    queryFn: () => fetchCourse(courseId),
  });
}
