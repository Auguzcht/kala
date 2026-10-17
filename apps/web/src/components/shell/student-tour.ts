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
  key?: string;
  search?: Record<string, string | boolean>;
  /** Element to highlight for this step. */
  selector: string;
  title: string;
  description: string;
  /** UI-only action: open a panel, flip a card, or toggle a tab/input.
   * Never use this for saving, grading, generation, retakes or sending. */
  click?: boolean;
  clickSelector?: string;
  /** Skip the click when this selector is already present. For toggles
   * whose open state is driven by data (the skill-review section
   * auto-opens when a queue exists) — clicking an already-open trigger
   * would collapse it mid-tour. */
  clickOnlyWhenClosed?: string;
  /** Editable sample text only. Never submits the form. */
  prefill?: { question: string; inputId: string };
  /** Observe the result of the student's own action; Next skips its
   * dependent steps. All action waits are bounded and have a Skip control. */
  studentAction?: { completeWhen: string; skipTo: string };
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
  // Tutor — editable draft, with sending left to the student.
  {
    route: "/course/tutor",
    key: "tutor",
    selector: "#tour-tutor-input",
    title: "Tutor",
    description: "Edit this sample question or write your own. Press Send yourself to ask Kala, or choose Next without sending.",
    prefill: {
      question: "Can you explain one key idea from this course with an example?",
      inputId: "tour-tutor-input",
    },
  },
  {
    route: "/course/tutor",
    selector: "#tour-tutor-response, #tour-tutor-input",
    title: "Tutor",
    description: "Replies appear here after you send a question. You can continue this tour without asking anything.",
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


export type HubTourContext = { skillId: string; setId?: string; completedOnly?: boolean };

/** All hub modes share one topic selected before leaving the current page. */
export function createStudentTour(context: HubTourContext): readonly TourStepConfig[] {
  const route = `/course/skill/${context.skillId}`;
  const hub = (selector: string, title: string, description: string, extra: Partial<TourStepConfig> = {}): TourStepConfig =>
    ({ route, selector, title, description, ...extra });
  const chat = (mode: string): TourStepConfig[] => [
    hub(`#tour-${mode}-dock-toggle`, "Ask about this topic", "Use the chat button to switch this dock from actions to a follow-up question.", { click: true, clickOnlyWhenClosed: `#tour-${mode}-dock-input` }),
    hub(`#tour-${mode}-dock-input`, "Try a follow-up", "This is an editable sample. Press Send yourself to ask Kala, or choose Next without sending.", {
      prefill: { question: "Can you explain this with one short example?", inputId: `tour-${mode}-dock-input` },
    }),
    hub(`#tour-${mode}-dock-toggle`, "Back to the action", "Close the input to restore the session controls. Sending a question is always your choice.", { click: true }),
  ];
  const preview = (): TourStepConfig => hub("#tour-test-start", "Test preview", "Choose Start test or Continue test yourself to open the questions, or skip this part of the tour.", {
    studentAction: { completeWhen: "#tour-practice-choices", skipTo: "tutor" },
    waitFor: "#tour-test-start:not(:disabled)",
    waitState: { selector: "main", description: "Loading the saved test…" },
  });
  const testSteps: TourStepConfig[] = context.completedOnly ? [
    hub("#tour-test-menu", "Your completed tests", "These sets are complete. Open a saved set yourself to view results and choose Retake this set. The tour never starts a retake.", {
      key: "test", search: { tab: "test" }, waitFor: "#tour-test-menu",
      waitState: { selector: "main", description: "Loading your tests…" },
    }),
    hub("#tour-test-new-set", "New set", "New set prepares another saved test only when you click it. You can continue the tour without creating anything."),
  ] : [
    ...(context.setId ? [
      { ...preview(), key: "test", search: { tab: "test", setId: context.setId } },
    ] : [
      hub("#tour-test-new-set", "Test", "Click New set yourself to prepare questions, or skip this part of the tour. The tour never creates a set.", {
        key: "test", search: { tab: "test" },
        studentAction: { completeWhen: "#tour-test-start", skipTo: "tutor" },
        waitFor: "#tour-test-new-set:not(:disabled)",
        waitState: { selector: "main", description: "Checking this topic's questions…" },
      }),
      preview(),
    ]),
    hub("#tour-practice-choices", "Answer a question", "Pick an answer to see feedback. Your click submits the answer; Skip this step leaves it unanswered.", {
      studentAction: { completeWhen: "#tour-practice-feedback", skipTo: "tutor" },
      waitFor: "#tour-practice-choices",
      waitState: { selector: "main", description: "Loading the question…" },
    }),
    hub("#tour-practice-feedback", "Test feedback", "The dock now offers Next question or See results, plus chat about the answer."),
    ...chat("test"),
  ];
  return [
    ...TOUR_STEPS.slice(0, 3),
    hub("#tour-lesson-explain", "Lesson", "Learn this topic, then use the dock to continue or ask a follow-up.", {
      search: { tab: "lesson" }, waitFor: "#tour-lesson-explain",
      waitState: { selector: "#tour-lesson-generating", description: "Preparing this topic's lesson…" },
    }),
    ...chat("lesson"),
    hub("#tour-lesson-continue", "Lesson controls", "Continue opens a check when this step has one. Teaching-only steps move to the next explanation.", { click: true }),
    hub("#tour-lesson-check, #tour-lesson-explain", "Check your understanding", "Pick an answer yourself to see feedback, or skip this step. The tour never answers a check for you.", {
      studentAction: { completeWhen: "#tour-lesson-check-feedback, #tour-lesson-explain", skipTo: "study" },
      waitFor: "#tour-lesson-check, #tour-lesson-explain",
      waitState: { selector: "main", description: "Opening the lesson step…" },
    }),
    hub("#tour-lesson-check-feedback, #tour-lesson-explain", "Lesson feedback", "Check feedback stays visible. The dock offers the next step or another try after answering."),
    hub("#tour-study-actions", "Study", "Choose Start studying, Review due or Study all yourself to enter a deck, or skip this part of the tour.", {
      key: "study", search: { tab: "study" },
      studentAction: { completeWhen: "#tour-study-dock", skipTo: "test" },
      waitFor: "#tour-study-actions",
      waitState: { selector: "main", description: "Loading this topic's study menu…" },
    }),
    hub("#tour-study-dock", "Recall first", "Show answer flips the card. It does not submit a rating.", {
      click: true, clickSelector: "#tour-study-show-answer",
      waitFor: "#tour-study-show-answer:not(:disabled), #tour-study-dock-secondary",
      waitState: { selector: "main", description: "Loading your deck…" },
    }),
    ...chat("study"),
    hub("#tour-study-dock", "Rate your recall", "Still learning repeats this card later in the session. Got it clears it from the queue. Only your own click saves a rating; Next continues the tour without rating this card."),
    ...testSteps,
    ...TOUR_STEPS.slice(3),
  ];
}
