import assert from "node:assert/strict";
import test from "node:test";
import type { Roster } from "../schema/instructor.schema.ts";
import { courseStanding, ordinal } from "../lib/standing.ts";

function roster(values: (number | null)[]): Roster {
  return { courseId: "course", students: values.map((readiness, index) => ({
    userId: `learner-${index}`, displayName: "Synthetic learner", pseudonym: "Learner",
    initials: "SL", readiness, band: "no-evidence", attempts: 0, evidenceCount: 0,
    accuracy: null, lastActiveAt: null, daysInactive: null, weakestSkillName: null,
    skillsWithEvidence: 0, skillsTotal: 15, status: "not-started",
  })) };
}

test("INSTR-REQ-012 course standing ranks measured learners, not the 200 percentile", () => {
  const data = roster([0.739, 0.55, ...Array<null>(23).fill(null)]);
  assert.equal(data.students.length, 25);
  assert.deepEqual(courseStanding(data, "course", "learner-0"), { rank: 1, total: 2, tied: false });
  assert.deepEqual(courseStanding(data, "course", "learner-1"), { rank: 2, total: 2, tied: false });
  assert.equal(courseStanding(data, "course", "learner-2"), null);
});

test("INSTR-REQ-012 tied readiness uses competition rank independent of triage sort", () => {
  const data = roster([0.7, 0.8, 0.8, null]);
  assert.deepEqual(courseStanding(data, "course", "learner-0"), { rank: 3, total: 3, tied: false });
  assert.deepEqual(courseStanding(data, "course", "learner-1"), { rank: 1, total: 3, tied: true });
  data.students.reverse();
  assert.deepEqual(courseStanding(data, "course", "learner-2"), { rank: 1, total: 3, tied: true });
});

test("INSTR-REQ-012 wrong course, unknown or unmeasured learner never invents a rank", () => {
  assert.equal(courseStanding(undefined, "course", "learner-0"), null);
  assert.equal(courseStanding(roster([]), "course", "learner-0"), null);
  assert.equal(courseStanding(roster([0.7]), "other-course", "learner-0"), null);
  assert.equal(courseStanding(roster([0.7]), "course", "missing"), null);
  assert.equal(courseStanding(roster([null, 0.7]), "course", "learner-0"), null);
});

test("INSTR-REQ-012 English ordinals include teen exceptions", () => {
  assert.deepEqual([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 111].map(ordinal),
    ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "111th"]);
});
