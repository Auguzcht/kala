// Shared config for the cross-page student walkthrough (DESIGN.md: the
// driver.js onboarding tour). Diagnostic, Tutor and Twin remain static;
// the hub section below pins Lesson, Study and Test to one prepared topic.
//
// Copy rule (DESIGN.md): student-facing text is plain topic language. No
// "Bloom's", no "RAG", no "your twin" until the closing Twin steps, where
// the analytical layer is allowed.
export type TourStepConfig = {
  /** A trailing /* follows the hub opened by a preceding click. */
  route: string;
  search?: Record<string, string | boolean>;
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
  tutorAsk?: { question: string; inputId?: string };
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


export type HubTourContext = { skillId: string; setId?: string };

/** All hub modes share one topic selected before leaving the current page. */
export function createStudentTour(context: HubTourContext): readonly TourStepConfig[] {
  const route = `/course/skill/${context.skillId}`;
  const hub = (selector: string, title: string, description: string, extra: Partial<TourStepConfig> = {}): TourStepConfig =>
    ({ route, selector, title, description, ...extra });
  const chat = (mode: string): TourStepConfig[] => [
    hub(`#tour-${mode}-dock-toggle`, "Ask about this topic", "Use the chat button to switch this dock from actions to a follow-up question.", { click: true }),
    hub(`#tour-${mode}-dock-input`, "Try a follow-up", "Next types and sends a sample question about the content on this card.", {
      tutorAsk: { question: "Can you explain this with one short example?", inputId: `tour-${mode}-dock-input` },
    }),
    hub(`#tour-${mode}-reply`, "Stay on the same topic", "Kala answers in this session. The dock lets you ask another question or return to the action.", {
      waitFor: `#tour-${mode}-reply`,
      waitState: { selector: `#tour-${mode}-dock`, description: "Waiting for your follow-up answer…" },
    }),
    hub(`#tour-${mode}-dock-toggle`, "Back to the action", "Close the input to restore the session controls.", { click: true }),
  ];
  return [
    ...TOUR_STEPS.slice(0, 3),
    hub("#tour-lesson-explain", "Lesson", "Learn this topic, then use the dock to continue or ask a follow-up.", {
      search: { tab: "lesson" }, waitFor: "#tour-lesson-explain",
      waitState: { selector: "#tour-lesson-generating", description: "Preparing this topic's lesson…" },
    }),
    ...chat("lesson"),
    hub("#tour-lesson-continue", "Lesson controls", "Continue opens a check when this step has one. Teaching-only steps move to the next explanation.", { click: true }),
    hub("#tour-lesson-check, #tour-lesson-explain", "Check your understanding", "When this step has a check, Next selects an answer. Otherwise the lesson continues with teaching.", {
      click: true, clickSelector: "#tour-first-choice",
      waitFor: "#tour-lesson-check, #tour-lesson-explain",
      waitState: { selector: "main", description: "Opening the lesson step…" },
    }),
    hub("#tour-lesson-check-feedback, #tour-lesson-explain", "Lesson feedback", "Check feedback stays visible. The dock offers the next step or another try after answering.", {
      waitFor: "#tour-lesson-check-feedback, #tour-lesson-explain",
      waitState: { selector: "#tour-lesson-check", description: "Checking your answer…" },
    }),
    hub("#tour-study-dock", "Study", "The same topic, now for recall. Show the answer before rating the card.", {
      search: { tab: "study", start: true, mode: "all" },
      waitFor: "#tour-study-dock-primary:not(:disabled)",
      waitState: { selector: "main", description: "Preparing this topic's cards…" },
      click: true, clickSelector: "#tour-study-dock-primary",
    }),
    hub("#tour-study-dock", "Rate your recall", "Still learning repeats this card later in the session. Got it clears it from this session's queue."),
    ...chat("study"),
    ...(context.setId ? [
      hub("#tour-test-start", "Saved test", "Reuse a saved test on this same topic. Start, continue, or open its results.", {
        search: { tab: "test", setId: context.setId }, click: true,
        waitFor: "#tour-test-start:not(:disabled)",
        waitState: { selector: "main", description: "Loading the saved test…" },
      }),
      hub("#tour-test-retake, #tour-practice-card", "Test sitting", "If this set is complete, Next starts a new retake. Otherwise it keeps your current sitting.", {
        click: true, clickSelector: "#tour-test-retake",
        waitFor: "#tour-test-retake:not(:disabled), #tour-practice-card",
        waitState: { selector: "main", description: "Loading the test sitting…" },
      }),
    ] : [
      hub("#tour-test-new-set", "Test", "Create a saved set for this same topic. Next activates the button once questions are available.", {
        search: { tab: "test" }, click: true,
        waitFor: "#tour-test-new-set:not(:disabled)",
        waitState: { selector: "main", description: "Checking this topic's questions…" },
      }),
      hub("#tour-test-start", "Test preview", "Preview the questions, then start this saved set.", {
        click: true, waitFor: "#tour-test-start:not(:disabled)",
        waitState: { selector: "main", description: "Preparing the test set…" },
      }),
    ]),
    hub("#tour-practice-choices", "Answer a question", "Next selects an answer. Feedback stays visible until you use the dock.", {
      click: true, clickSelector: "#tour-first-choice", waitFor: "#tour-first-choice:not(:disabled)",
      waitState: { selector: "main", description: "Loading the question…" },
    }),
    hub("#tour-practice-feedback", "Test feedback", "The dock now offers Next question or See results, plus chat about the answer.", {
      waitFor: "#tour-practice-feedback",
      waitState: { selector: "#tour-test-dock", description: "Checking the answer…" },
    }),
    ...chat("test"),
    ...TOUR_STEPS.slice(3),
  ];
}
