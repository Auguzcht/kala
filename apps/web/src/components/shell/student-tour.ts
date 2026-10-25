// Shared config for the cross-page student walkthrough (DESIGN.md: the
// driver.js onboarding tour). Diagnostic, Tutor and Twin remain static;
// the hub section below pins Lesson, Study and Test to one prepared topic.
//
// Copy rule (DESIGN.md): student-facing text is plain topic language. No
// "Bloom's", no "RAG", no "your twin" until the closing Twin steps, where
// the analytical layer is allowed.
export type TourStepConfig = {
  /** Concrete route, parameter pattern or trailing hub wildcard. */
  route: string;
  key?: string;
  search?: Record<string, string | boolean>;
  /** Element to highlight for this step. */
  selector: string;
  /** Conditional state: briefly wait, then skip without creating it. */
  optional?: boolean;
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

const diagnostic: TourStepConfig[] = [
  { route: "/course/diagnostic", selector: '[data-tour="diagnostic-header"]', optional: true, title: "Find your starting point", description: "Answer topics that have questions ready and no learning evidence yet. After you submit, the results show your skill progression and a link to your twin." },
  { route: "/course/diagnostic", selector: "#tour-diagnostic-choices", optional: true, title: "Answer at your pace", description: "Choose an answer for each topic. Submit diagnostic saves the whole baseline; this tour leaves your answers untouched." },
  { route: "/course/diagnostic", selector: "[data-diagnostic-results]", optional: true, title: "Your baseline results", description: "After you submit, this panel shows how your skill profile changed. Open your twin to explore it; no answer key is shown here." },
];
const tutor: TourStepConfig[] = [
  { route: "/course/tutor", key: "tutor", selector: "#tour-tutor-input", title: "Ask Kala", description: "Edit this sample or write your own question. Only Send asks Kala. While a reply is being prepared, a thinking indicator appears in the conversation.", prefill: { question: "Can you explain one key idea from this course with an example?", inputId: "tour-tutor-input" } },
  { route: "/course/tutor", selector: '[data-tour="tutor-history"], [data-tour="tutor-history-mobile"]', title: "Keep track of your chats", description: "Recents keeps your saved chats. When management is available, use a chat menu to rename or pin it; pinned chats appear above Recents. New chat opens an empty draft. On a small screen, Open chat history reveals the list." },
  { route: "/course/tutor", selector: '[data-tour="tutor-attach"]', title: "Attach course material", description: "Choose Attach a file or drop a PDF, text or Markdown file into the conversation. Files are staged first and uploaded when you send. This tour does not attach or upload anything." },
];
const twin: TourStepConfig[] = [
  { route: "/course/twin", selector: "#tour-twin-readiness", title: "Your learning, measured", description: "Board readiness summarizes your current learning evidence. A dash means there is not enough evidence yet." },
  { route: "/course/twin", selector: "#tour-twin-radar", title: "Explore your skill profile", description: "The chart groups mastery by Bloom’s level. Read it alongside the skill breakdown to find topics to revisit." },
  { route: "/course/twin", selector: '[data-tour="twin-ledger"]', title: "Read the evidence", description: "The ledger shows the last 20 learning events. Use its pages to review the evidence behind your current profile." },
];
export const TOUR_STEPS: readonly TourStepConfig[] = [...diagnostic, ...tutor, ...twin];

export function studentTourDismissKey(userId: string): string {
  return `kala.student.tour.${userId}`;
}
export type HubTourContext = { skillId: string; setId?: string; completedOnly?: boolean };

/** One prepared topic; no automatic lesson checks, ratings or test starts. */
export function createStudentTour(context: HubTourContext): readonly TourStepConfig[] {
  const route = `/course/skill/${context.skillId}`;
  const hub = (selector: string, title: string, description: string, extra: Partial<TourStepConfig> = {}): TourStepConfig => ({ route, selector, optional: true, title, description, ...extra });
  return [
    ...diagnostic,
    hub("#tour-lesson-explain", "Learn one topic", "Read the explanation, then use Continue for the next step or check. Only your own answer checks your understanding.", { search: { tab: "lesson" } }),
    hub("#tour-lesson-dock-toggle", "Ask about this topic", "The chat button opens a follow-up draft in the dock. Sending a question is always your choice."),
    hub("#tour-study-actions", "Study this topic", "Choose Start studying, Review due or Study all to enter a deck. At the end, Go through these again replays those cards locally; Check for more cards refreshes availability. The tour starts neither.", { key: "study", search: { tab: "study" } }),
    hub("#tour-study-dock", "Recall and review", "Show answer reveals the card. Still learning repeats it later; Got it clears it from the session queue. Only your own rating saves recall evidence."),
    hub('[data-tour="study-complete"]', "At the end of a deck", "Go through these again replays these cards locally. Check for more cards refreshes the deck for more available cards. The tour chooses neither."),
    hub("#tour-test-menu", "Your saved tests", "Open a saved set to continue it or view its results. New set prepares more questions only when you choose it.", { key: "test", search: { tab: "test", ...(context.setId ? { setId: context.setId } : {}) } }),
    hub("#tour-test-start", "Start when you are ready", "Start test or Continue test opens the questions. The tour does not start, answer or retake a test."),
    hub('[data-tour="test-results"]', "Review your results", "Results show your score, mastery change and questions to review. Review missed, Retake this set and New set are your choices; the tour leaves them untouched."),
    ...tutor,
    ...twin,
  ];
}
