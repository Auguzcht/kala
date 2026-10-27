import type { Roster, RosterRow } from "@/features/instructor";

export function progressTourLearner(roster: Roster | undefined, courseId: string): RosterRow | undefined {
  if (!roster || roster.courseId !== courseId) return;
  return roster.students.filter((row) => row.evidenceCount > 0 || row.attempts > 0 || row.skillsWithEvidence > 0)
    .sort((a, b) => b.evidenceCount - a.evidenceCount || b.attempts - a.attempts
      || b.skillsWithEvidence - a.skillsWithEvidence || a.userId.localeCompare(b.userId))[0];
}

/** Match the roster's existing name/pseudonym/skill search without assuming unique names. */
export function progressLearnerSearch(roster: Roster, learner: RosterRow): string | undefined {
  return [learner.pseudonym, learner.displayName].find((value) => {
    const query = value.trim().toLowerCase();
    return query && roster.students.filter((row) =>
      [row.displayName, row.pseudonym, row.weakestSkillName ?? ""].some((text) => text.toLowerCase().includes(query)),
    ).length === 1;
  });
}
