// Shared config for the cross-page student walkthrough (DESIGN.md: the
// driver.js onboarding tour; student path: diagnostic → lessons → practice →
// tutor → twin). Every page follows the same overview → example → outcome
// shape, several steps deep — the walkthrough is ~16 real highlights across
// 5 pages by design, not one popover per page.
//
// Copy rule (DESIGN.md): student-facing text is plain topic language. No
// "Bloom's", no "RAG", no "your twin" until the closing Twin steps, where
// the analytical layer is allowed.
export type TourStepConfig = {
  route: string;
  /** Element to highlight for this step. */
  selector: string;
  title: string;
  description: string;
  /** Click a target when the user hits Next (default: the highlighted
   * element; override with clickSelector when the click target differs —
   * e.g. the Lessons overview highlights the module list but clicks the
   * first lesson card). */
  click?: boolean;
  clickSelector?: string;
  /** Skip the click when this selector is already present. For toggles
   * whose open state is driven by data (the skill-review section
   * auto-opens when a queue exists) — clicking an already-open trigger
   * would collapse it mid-tour. */
  clickOnlyWhenClosed?: string;
  /** Ask the tutor a canned question when Next is hit: fill the input and
   * submit through the same path the Ask button uses. */
  tutorAsk?: { question: string };
  /** Wait for this selector before highlighting (never highlight against a
   * skeleton). If missing, show `waitState` instead and poll until ready. */
  waitFor?: string;
  waitState?: { selector: string; description: string };
};

export const TOUR_STEPS: readonly TourStepConfig[] = [
  // Diagnostic — baseline: overview, choices, submit.
  {
    route: "/course/diagnostic",
    selector: "#tour-diagnostic-card",
    title: "Diagnostic",
    description: "This is your baseline. One question per topic.",
  },
  {
    route: "/course/diagnostic",
    selector: "#tour-diagnostic-choices",
    title: "Diagnostic",
    description: "Pick the closest match — this isn't graded like an exam.",
  },
  {
    route: "/course/diagnostic",
    selector: "#tour-diagnostic-submit",
    title: "Diagnostic",
    description: "Submit once every topic's answered. Your twin updates right after.",
  },
  // Lessons — module list, real lesson, continue, the check, the feedback.
  {
    route: "/course/lessons",
    selector: "#tour-lessons-picker",
    title: "Lessons",
    description: "Lessons are grouped by topic, one skill at a time.",
    click: true,
    clickSelector: "#tour-lessons-first-card",
  },
  {
    route: "/course/lessons",
    selector: "#tour-lesson-explain",
    title: "Lessons",
    description: "Kala teaches one skill at a time — explain, then check.",
    waitFor: "#tour-lesson-explain",
    waitState: {
      selector: "#tour-lesson-generating",
      description: "Kala is writing this lesson…",
    },
  },
  {
    route: "/course/lessons",
    selector: "#tour-lesson-continue",
    title: "Lessons",
    description: "You confirm you're ready before moving on.",
    click: true,
  },
  {
    route: "/course/lessons",
    selector: "#tour-lesson-check",
    title: "Lessons",
    description: "One quick check on what Kala just taught — correct answers advance the lesson.",
    click: true,
    clickSelector: "#tour-first-choice",
  },
  {
    route: "/course/lessons",
    selector: "#tour-lesson-check-feedback",
    title: "Lessons",
    description: "Right or wrong, you see why — and your twin moves.",
  },
  // Practice — landing (choose or take the recommendation), then the
  // session: overview, choices, graded result (the twin-moved moment).
  // The landing step is new here — Practice used to land straight on the
  // session panel; now that a topic choice comes first (Stage 3 of the
  // AI overhaul), #tour-practice-card doesn't exist until that choice is
  // made, so the tour has to make it the same way Lessons' own tour
  // already clicks through its landing grid.
  {
    route: "/course/practice",
    selector: "#tour-practice-picker",
    title: "Practice",
    description: "Pick a topic, or take the recommended one.",
    click: true,
    clickSelector: "#tour-practice-recommended",
  },
  {
    route: "/course/practice",
    selector: "#tour-practice-card",
    title: "Practice",
    description: "Targeted at your weakest skill, not random.",
  },
  {
    route: "/course/practice",
    selector: "#tour-practice-choices",
    title: "Practice",
    description: "Pick the closest match — the result shows why, either way.",
    click: true,
    clickSelector: "#tour-first-choice",
  },
  {
    route: "/course/practice",
    selector: "#tour-practice-feedback",
    title: "Practice",
    description:
      "Right or wrong, you see why — and your twin moves. Streak and XP tick up as you practice.",
  },
  // Tutor — ask a real question, highlight the grounded answer.
  {
    route: "/course/tutor",
    selector: "#tour-tutor-input",
    title: "Tutor",
    description: "Ask about anything in this course.",
    tutorAsk: {
      question: "What's the difference between analog and digital signals?",
    },
  },
  {
    route: "/course/tutor",
    selector: "#tour-tutor-response",
    title: "Tutor",
    description:
      "It teaches and cites your course content — never hands back graded answers.",
    waitFor: "#tour-tutor-response",
    waitState: {
      selector: "#tour-tutor-thinking",
      description: "Kala is thinking…",
    },
  },
  // Twin — the one place the analytical layer is allowed.
  {
    route: "/course/twin",
    selector: "#tour-twin-readiness",
    title: "Your learning, measured",
    description: "One number — your overall board readiness.",
  },
  {
    route: "/course/twin",
    selector: "#tour-twin-radar",
    title: "Your learning, measured",
    description:
      "Mastery broken out by Bloom's level. Each spoke is a level, averaged across its skills.",
  },
  {
    route: "/course/twin",
    selector: "#tour-twin-activity",
    title: "Your learning, measured",
    description: "Every answer you give updates this live.",
  },
];

// Per-user dismissal key (localStorage). "dismissed" = banner hidden forever
// (via "Got it" or finishing the tour); anything else (absent) = first run,
// banner eligible.
export function studentTourDismissKey(userId: string): string {
  return `kala.student.tour.${userId}`;
}
