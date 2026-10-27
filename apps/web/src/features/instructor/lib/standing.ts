import type { Roster } from "@/features/instructor";

export type CourseStanding = { rank: number; total: number; tied: boolean };

export function courseStanding(
  roster: Roster | undefined,
  courseId: string,
  userId: string,
): CourseStanding | null {
  if (!roster || roster.courseId !== courseId) return null;
  const measured = roster.students.filter(
    (row): row is typeof row & { readiness: number } =>
      row.readiness !== null && Number.isFinite(row.readiness),
  );
  const learner = measured.find((row) => row.userId === userId);
  if (!learner) return null;
  return {
    rank: 1 + measured.filter((row) => row.readiness > learner.readiness).length,
    total: measured.length,
    tied: measured.filter((row) => row.readiness === learner.readiness).length > 1,
  };
}

export function ordinal(value: number): string {
  const lastTwo = value % 100;
  const suffix = lastTwo >= 11 && lastTwo <= 13
    ? "th"
    : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[value % 10] ?? "th";
  return `${value}${suffix}`;
}
