// Shared config for the instructor walkthrough (DESIGN.md: driver.js
// onboarding; instructor path: KPI strip → roster → triage sheet → needs
// support → trends → heatmap → one learner's record). Mirrors the student
// tour's shape (student-tour.ts) — same TourStepConfig type, same
// cross-page store-driven runner (TourRunner.tsx), different steps and
// dismissal key.
//
// The story the steps tell is the sheet-vs-record distinction: the roster
// progress row opens the triage SHEET (standing + decide). Later Next
// opens the same learner’s RECORD for mastery and activity history,
// without an extra transition stop or a dependency on support flags.
//
// Copy rule (DESIGN.md): instructor-facing text is direction, not
// description, and never verdict language. "Needs support", not "failing";
// "your decision", not "approval workflow".

import type { TourPresentationStep } from "@/components/shell/TourRunner";

export const INSTRUCTOR_TOUR_STEPS: readonly TourPresentationStep[] = [
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
    progressLearner: "select",
    fallbackDescription: "A learner with recorded progress could not be shown in this roster view. Select Next to continue.",
    optional: true,
    title: "Triage a learner",
    description:
      "The tour selects a learner with recorded progress from the whole roster. Next opens their triage sheet while the roster stays underneath.",
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
    optional: true,
    title: "Triage a learner",
    description:
      "Standing at a glance: readiness, class standing, accuracy, and momentum — the numbers that only exist by comparison. This is the whole sheet — triage, not a deep dive.",
    waitFor: "#tour-standing",
  },
  {
    route: "/class",
    selector: "#tour-decide-center",
    optional: true,
    title: "The gate",
    description:
      "Kala proposes next actions for this learner, each with the evidence behind it. Nothing reaches the learner until you decide.",
  },
  {
    route: "/class",
    selector: "#tour-standing",
    optional: true,
    title: "Triage a learner",
    description:
      "Close the sheet and keep triaging — or open the full record for the deep dive.",
    click: true,
    clickSelector: "[data-slot='sheet-close']",
  },
  // ---- Back on the overview: needs support, then the charts ------------
  {
    route: "/class",
    selector: "#at-risk-list, #tour-at-risk-first-flag",
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
  // ---- Skill mapping and review: the setup layer (HITL) -----------------
  {
    route: "/class",
    selector: "#tour-skill-review-trigger",
    title: "Skill mapping and review",
    description:
      "The setup layer, collapsed because it is not daily work. The orange badge is the queue: every pending skill was AI-drafted from the course's content and is waiting on a human decision.",
    click: true,
    // The section auto-opens when a queue exists — clicking an
    // already-open trigger would collapse it. Skip the click in that
    // case; only click when the panel is actually closed.
    clickOnlyWhenClosed: "#tour-skill-review-panel",
  },
  {
    route: "/class",
    selector: "#tour-skill-review-panel",
    title: "Skill mapping and review",
    description:
      "Each proposal shows its Bloom's level, weight, and where it came from — a module, or a flagged possible duplicate of a skill already approved elsewhere.",
    waitFor: "#tour-skill-review-panel",
  },
  {
    route: "/class",
    selector: "#tour-skill-approve",
    progressLearner: "record",
    explainOnly: true,
    fallbackDescription: "When proposals are available, Approve makes a skill live and Reject leaves it out. Select Next to continue without changing anything.",
    optional: true,
    title: "Skill mapping and review",
    description:
      "Approve makes a proposed skill available, while Reject leaves it out. Select Next to continue without making a decision.",
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
    activateSelector: "#tour-tab-decide",
    title: "Decide",
    description:
      "The same gate as the sheet: evidence-backed proposals, your decision, nothing reaching the learner until then.",
    waitFor: "#tour-decide-center",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-run-analysis",
    activateSelector: "#tour-tab-decide",
    explainOnly: true,
    fallbackDescription: "Run analysis prepares recommendations only when you choose it outside the tour. Select Next to continue without running it.",
    title: "Decide",
    description:
      "Run analysis prepares recommendations from the learner’s current evidence only when you choose it. The tour never runs an analysis.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-rec-card",
    activateSelector: "#tour-tab-decide",
    explainOnly: true,
    fallbackDescription: "Recommendations appear here when available. The tour does not run analysis to create them.",
    optional: true,
    title: "Decide",
    description:
      "Every recommendation shows the evidence it was derived from — you are asked to exercise judgement, not rubber-stamp a score.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-decision-buttons",
    activateSelector: "#tour-tab-decide",
    explainOnly: true,
    fallbackDescription: "When recommendations are available, Approve assigns one and Decline rejects it. Select Next to continue without recording a decision.",
    optional: true,
    title: "Decide",
    description:
      "Approve assigns a recommendation, Modify changes it and Decline rejects it. Select Next to continue without recording a decision.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-readiness",
    activateSelector: "#tour-tab-mastery",
    title: "Readiness",
    description: "This number and ring summarise the learner's current mastery estimate. Use the skill-by-skill view next to see where that estimate comes from.",
    waitFor: "#tour-record-readiness",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-radar",
    activateSelector: "#tour-tab-mastery",
    title: "Mastery across skills",
    description:
      "Compare the mastery profile across Bloom's levels and check which skills still have no evidence.",
    waitFor: "#tour-record-radar",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-intervene",
    activateSelector: "#tour-tab-mastery",
    explainOnly: true,
    fallbackDescription: "Suggested interventions appear here when available. Select Next to continue without assigning work.",
    title: "Where to intervene",
    description: "Weakest first — the intervention list that decides what to assign.",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-readiness-trend",
    activateSelector: "#tour-tab-activity",
    title: "Readiness over time",
    description: "Follow the learner's recorded readiness snapshots over time. A trend appears once enough snapshots have been saved.",
    waitFor: "#tour-record-readiness-trend",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-activity",
    activateSelector: "#tour-tab-activity",
    title: "Practice and activity",
    description: "Review recorded correct and missed outcomes. The activity badges show the available events by learning type.",
    waitFor: "#tour-record-activity",
  },
  {
    route: "/class/student/$uid",
    selector: "#tour-record-ledger",
    activateSelector: "#tour-tab-activity",
    title: "Evidence ledger",
    description:
      "Review the recent learning evidence behind this record. Use the ledger’s pages to move through the available events.",
    waitFor: "#tour-record-ledger",
  },
];

// Per-user dismissal key (localStorage). "dismissed" = banner hidden
// forever (via "Got it" or finishing the tour); anything else = first run.
export function instructorTourDismissKey(userId: string): string {
  return `kala.instructor.tour.${userId}`;
}
