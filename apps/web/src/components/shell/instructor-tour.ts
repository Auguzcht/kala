// Shared config for the instructor walkthrough (DESIGN.md: driver.js
// onboarding; instructor path: KPI strip → roster → triage sheet → needs
// support → trends → heatmap → one learner's record). Mirrors the student
// tour's shape (student-tour.ts) — same TourStepConfig type, same
// cross-page store-driven runner (TourRunner.tsx), different steps and
// dismissal key.
//
// The story the steps tell is the sheet-vs-record distinction: the roster
// row opens the triage SHEET (standing + decide, the "who do I decide for
// right now" task), and the needs-support flag or the sheet's "Open full
// record" link leads to the RECORD page (the deep dive — mastery and
// activity history).
//
// Copy rule (DESIGN.md): instructor-facing text is direction, not
// description, and never verdict language. "Needs support", not "failing";
// "your decision", not "approval workflow".

import type { TourStepConfig } from "@/components/shell/student-tour";

export const INSTRUCTOR_TOUR_STEPS: readonly TourStepConfig[] = [
  // ---- Class overview: the six numbers first ---------------------------
  {
    route: "/class",
    selector: "#tour-cohort-kpis",
    title: "Your class, measured",
    description:
      "Six numbers before anything else: how many learners, how many are moving, where the cohort sits, and how many proposals are waiting on your decision.",
  },
  {
    route: "/class",
    selector: "#roster-panel",
    title: "Class roster",
    description:
      "Every enrolled student, sorted by who needs you first. Real names, because you are the teacher of record. Flip the de-identify switch for screen-sharing.",
  },
  {
    route: "/class",
    selector: "#tour-roster-search",
    title: "Class roster",
    description: "Search by name or skill when the class is big enough to search.",
  },
  {
    route: "/class",
    selector: "#tour-roster-filter",
    title: "Class roster",
    description: "Filter by status — the roster is triaged, not alphabetical.",
  },
  {
    route: "/class",
    selector: "#tour-roster-first-row",
    title: "Triage a learner",
    description:
      "Click a row to open the triage sheet — the roster stays underneath, so triaging three learners in a row costs no re-orientation.",
    click: true,
  },
  // ---- The triage sheet (standing + decide only) ------------------------
  // Deliberately short: the sheet is triage, and the record page later
  // goes deep on the same gate — repeating the full decision anatomy here
  // would make the two sections redundant. Standing, the gate in one line,
  // then close and keep triaging.
  {
    route: "/class",
    selector: "#tour-standing",
    title: "Triage a learner",
    description:
      "Standing at a glance: readiness, class standing, accuracy, and momentum — the numbers that only exist by comparison. This is the whole sheet — triage, not a deep dive.",
    waitFor: "#tour-standing",
  },
  {
    route: "/class",
    selector: "#tour-decide-center",
    title: "The gate",
    description:
      "Kala proposes next actions for this learner, each with the evidence behind it. Nothing reaches the learner until you decide.",
  },
  {
    route: "/class",
    selector: "#tour-standing",
    title: "Triage a learner",
    description:
      "Close the sheet and keep triaging — or open the full record for the deep dive.",
    click: true,
    clickSelector: "[data-slot='sheet-close']",
  },
  // ---- Back on the overview: needs support, then the charts ------------
  {
    route: "/class",
    selector: "#at-risk-list",
    title: "Needs support",
    description:
      "Evidence-triggered flags with the specific reason behind each one. Supportive wording, never a verdict on a student.",
  },
  {
    route: "/class",
    selector: "#cohort-analytics",
    title: "Is the class moving?",
    description:
      "Readiness over time, practice volume, mastery mix, and the weakest skills across the class — the reteach list.",
  },
  {
    route: "/class",
    selector: "#tour-tab-heatmap",
    title: "Skills × Bloom's",
    description:
      "The same evidence arranged by Bloom's level — where the class is strong and where it is thin, level by level.",
    click: true,
  },
  {
    route: "/class",
    selector: "#heatmap-panel",
    title: "Skills × Bloom's",
    description:
      "Rows are learners, columns are skills under their Bloom's level. Color plus a letter — never color alone.",
    waitFor: "#heatmap-panel",
  },
  // ---- Cross to one learner's record via a needs-support flag ----------
  {
    route: "/class",
    selector: "#tour-at-risk-first-flag",
    title: "One learner",
    description:
      "Open the full record — the deep dive that needs width: mastery instruments and the evidence ledger.",
    click: true,
  },
  // ---- The record page (deep dive) --------------------------------------
  // Every tab is opened by the tour itself — Decide, Mastery, Activity —
  // so the tab structure is part of the walkthrough, not something the
  // user happens to click. Decide is the default tab, but the tour clicks
  // its trigger anyway for the explicit "here is the tab you work in"
  // beat before diving into its content.
  {
    route: "/class/student/$uid",
    selector: "#tour-standing",
    title: "One learner",
    description:
      "The same standing block as the sheet — this page adds everything that needs room to breathe.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-tab-decide",
    title: "Decide",
    description: "Three tabs, three tasks. Decide first, deliberately — the teacher came here to do something.",
    click: true,
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-decide-center",
    title: "Decide",
    description:
      "The same gate as the sheet: evidence-backed proposals, your decision, nothing reaching the learner until then.",
    waitFor: "#tour-decide-center",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-run-analysis",
    title: "Decide",
    description:
      "Generate or regenerate this learner's recommendations from their current twin.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-rec-card",
    title: "Decide",
    description:
      "Every recommendation shows the evidence it was derived from — you are asked to exercise judgement, not rubber-stamp a score.",
    waitFor: "#tour-rec-card",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-decision-buttons",
    title: "Decide",
    description:
      "Three real outcomes: approve, modify if the activity is wrong, or decline with a reason that stays in the audit trail.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-tab-mastery",
    title: "Mastery",
    description: "Where the learner's understanding actually sits, skill by skill.",
    click: true,
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-radar",
    title: "Mastery",
    description:
      "The twin's radar, broken out by Bloom's level — and where to intervene, weakest first.",
    waitFor: "#tour-record-radar",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-intervene",
    title: "Mastery",
    description: "Weakest first — the intervention list that decides what to assign.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-tab-activity",
    title: "Activity",
    description: "The evidence behind every number — trends, volume, and the ledger.",
    click: true,
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-ledger",
    title: "Activity",
    description:
      "The append-only evidence ledger. Every recommendation traces back to these rows — nothing here is a guess Kala cannot show its work for.",
    waitFor: "#tour-record-ledger",
  },
];

// Per-user dismissal key (localStorage). "dismissed" = banner hidden
// forever (via "Got it" or finishing the tour); anything else = first run.
export function instructorTourDismissKey(userId: string): string {
  return `kala.instructor.tour.${userId}`;
}
