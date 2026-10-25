import type { TwinSkill } from "@/features/twin/schema/twin.schema";

// Skills grouped by TOPIC (module_ref), not by Bloom's level — a student
// choosing what to work on wants "what topic is this," not "what
// cognitive tier." Skills without a module land in "Other topics" so
// nothing is hidden. Current contract:
// docs/features/study/README.md#learning-surface-boundaries. Practice and Flashcards both
// need the exact same grouping for their own topic-landing pages now, one
// implementation, not three copies.
export function groupByModule(skills: TwinSkill[]): [string, TwinSkill[]][] {
  const byModule = new Map<string, TwinSkill[]>();
  for (const s of skills) {
    const key = s.moduleRef?.trim() || "Other topics";
    byModule.set(key, [...(byModule.get(key) ?? []), s]);
  }
  return [...byModule.entries()].sort((a, b) =>
    a[0] === "Other topics" ? 1 : b[0] === "Other topics" ? -1 : a[0].localeCompare(b[0])
  );
}
