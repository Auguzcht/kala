---
feature: tour
req_prefix: TOUR
owner_role: product owner
status: active
code:
  web: [apps/web/src/components/shell/TourRunner.tsx, apps/web/src/components/shell/student-tour.ts, apps/web/src/components/shell/instructor-tour.ts]
  api: []
  worker: []
  db: []
tests: [apps/web/src/components/shell/tests/tour.browser.mjs]
---

# Student and instructor walkthroughs

## Purpose
Orient students and instructors within the real workspace using guided highlights, local navigation and editable examples. Tours may point at a learning action but must leave grading, saving, sending, generation and retakes to the user's own explicit action.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Start/dismiss/restart their walkthrough; skip real learning actions | Have the runner rate/answer/send/start a test for them |
| instructor/admin | Walk through roster, triage, charts, skill review and learner record | Have the runner approve/reject/analyze/assign for them |
| tour runner | Navigate, open UI panels/tabs, flip a card, prefill an empty draft | Click persistence or model-call actions |

## Requirements

### TOUR-REQ-001: Offer a user-controlled walkthrough with local dismissal
- Rule: shell confirmation starts the tour; Got it and completion persist a role-specific per-user localStorage dismissal key. Header affordance can restart. Escape/overlay/close clears active step and leaves the user on the current page; no forced return. Active step/context lives in Zustand across shell routes.
- Acceptance: dismissed users do not see the first-use banner; finishing hides it; exit preserves navigation. Dismissal is local to browser/user, not synchronized across devices.
- Status: implemented
- Verified by: static `CourseShell.tsx`, `InstructorShell.tsx`, `TourRunner.tsx::advanceTo`, `onDestroyed`; `studentTourDismissKey`, `instructorTourDismissKey`. No committed tour-specific automated/browser test is present.

### TOUR-REQ-002: Choose a prepared topic and reuse saved test context
- Rule: before student navigation, fetch bank status and saved sets; in bank mode choose usable non-no_material skill with >=5 MCQs. Legacy mode requires cached ready lesson or module-associated saved set >=5. Rank cached lesson, current topic and existing sets; pin lesson/study/test steps to that one skill. Prefer an unfinished saved set; completed-only context must not automatically retake/create a set.
- Acceptance: no eligible topic leaves the user in place with availability message; cancelling confirmation invalidates pending selection; test creation/start/retake remain explicit student actions.
- Status: implemented
- Verified by: static `CourseShell.tsx::startTour` and `student-tour.ts::createStudentTour`. No real-course availability acceptance is claimed.

### TOUR-REQ-003: Observe learning actions without performing them
- Rule: copy follows the current header, answering and results surfaces; Tutor covers history groups, rename/pin and file attach; Study explains end-of-deck replay versus checking for more cards; Test explains saved results; Twin explains the recent evidence ledger. Optional screens are skipped rather than created. Click steps are UI-only. StudentAction steps observe completion selectors and provide Skip, skipping dependent steps. Prefill only writes to an empty textarea; never submits or overwrites a draft. Student must choose test creation/start, answer checks/questions, rate recall and send tutor text. Instructor tour highlights decision buttons without clicking them.
- Acceptance: Next/Skip never makes an answer, rating, retake, recommendation decision or tutor send request. Draft examples remain editable. Learner actions taken manually during the tour are normal real actions.
- Status: partial
- Verified by: static `TourStepConfig` restrictions, `TourRunner.tsx::prefillInput`, `skipAction`, `student-tour.ts` and `instructor-tour.ts` click definitions. There is no network-spy/browser test proving the no-write invariant, and normal destination GETs can write content/queue state (finding below).

### TOUR-REQ-004: Wait for real targets and skip unavailable steps predictably
- Rule: bind route/search before driving; support instructor student-ID paths and hub wildcard matching. Wait up to 8 seconds for a normal visible target; explicitly optional targets wait at most 1.2 seconds. Data wait states and real student-action waits are bounded to 120 seconds. Unavailable targets skip to the next available step with one short message per run; action timeout skips its dependent sequence. Each step checks its own visible target, including conditional Diagnostic/results, roster and recommendation states; cleanup destroys obsolete instances. Back restores earlier available steps without repeating a UI click. Learner routes reuse an actual visited ID or follow a UI-only record link; never navigate to a literal placeholder. Missing learner context skips the record sequence instead of inventing a learner.
- Acceptance: no highlight anchors to a missing skeleton target; route transitions resume once matched; completed Diagnostic, no material, empty roster and empty recommendations continue cleanly. Next, Skip, Back and Escape work on desktop and at 375px.
- Status: partial
- Verified by: static `TourRunner.tsx`, `tour-route.ts`, `lib/wait-for-element.ts`. Browser timing, empty-state coverage and responsive popover placement have not been run in this lane.

### TOUR-REQ-005: Honor reduced motion and accessible orientation
- Rule: use Driver.js progress/close controls; scroll targets into view before positioning; disable smooth scrolling under prefers-reduced-motion. Copy describes topics/actions plainly and uses supportive instructor language.
- Acceptance: keyboard close exits; reduced-motion navigation uses auto scrolling; highlights/controls remain usable at desktop and 375px.
- Status: partial
- Verified by: static `TourRunner.tsx` useReducedMotion and driver options. Keyboard/focus, contrast, mobile positioning and reduced-motion end-to-end acceptance remain manual unknowns; hardcoded overlay token exception is recorded below.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /courses/{course_id}/bank/status | Student availability selection | Existing session/enrollment | Existing feature endpoint; may wake background bank work |
| GET /practice/{course_id}/sets | Read saved set context | Existing session | Existing feature endpoint; no create/retake by runner |

There is no tour backend endpoint or tour database table. Navigation mounts ordinary feature screens; those screens may read/generate content using their own APIs. User-initiated actions retain their normal persistence and cost.

## Data
Tour-specific persistence is only localStorage dismissal per user/role; ephemeral step/context is Zustand. The runner has no service-role client, no model client and no direct DB writes. It uses actual feature data rather than a synthetic learner record. A claim of zero total writes across all mounted feature routes is not established.

## AI usage (if any)
No direct model call from the runner or sample-text generation. Examples are deterministic strings; sending them remains the student's action. Navigating to a lesson with no cached ready content can still invoke normal first-open generation, and availability checks can wake bank work.

## Edge cases and known limits
- Missing/removed or hidden anchors are skipped; an empty class still walks through its available overview targets and omits learner-dependent steps.
- Optional results/Study-completion steps never create a session, submit answers or rate cards to reach their targets. The normal flow may skip them; the browse-step copy also explains the eventual end controls.
- Legacy availability can accept a cached ready lesson without five prepared questions, despite the unavailable message referring to five questions.
- Driver options do not independently prove accessibility; focus/mobile acceptance remains outstanding.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `docs/features/README.md:22` (tour never writes); `apps/web/src/components/shell/CourseShell.tsx:214` (bank status); `services/api/app/routers/bank.py:56` (wake); `services/api/app/routers/lessons.py:44` (GET generation) | Runner avoids explicit learning mutations, but normal reads/navigation can cause operational/content writes. | Define the invariant as no automatic learner evidence/actions, or add a read-only tour route mode; prove with network-spy acceptance. |
| `AGENTS.md:39` (tokens only); `apps/web/src/components/shell/TourRunner.tsx:39` (OVERLAY_COLOR literal) | Overlay is hardcoded rgba rather than a design token. | Review token replacement in an authorized shared-UI task. |
| `apps/web/src/components/shell/CourseShell.tsx:220` (legacy availability); `apps/web/src/components/shell/CourseShell.tsx:231` (five-question message) | Legacy ready lesson can qualify without five bank MCQs; message describes a stronger precondition. | Make message mode-aware or deliberately tighten precondition with UI acceptance tests. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked tour runner/config and topic preparation against the integrated CourseShell. User-action waits, draft-only examples and topic selection remain as described; source anchors were refreshed after shell changes. U/G changes do not prove tour acceptance: rehearsal remains FG-5. No dev server, browser tour or automatic learning action was run. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Refresh current UI anchors/copy; skip unavailable conditional steps; add Back and synthetic zero-mutation acceptance | User-authorized TOUR-REFRESH | TOUR-REQ-001, TOUR-REQ-003, TOUR-REQ-004, TOUR-REQ-005 |
| 2026-10-25 | Specify per-step visible-target checks, bounded optional skips and remembered concrete learner routes before runner changes | TOUR-REFRESH continuation in the existing UI worktree | TOUR-REQ-001, TOUR-REQ-003, TOUR-REQ-004, TOUR-REQ-005 |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | TOUR-REQ-001 through TOUR-REQ-005 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | TOUR requirements above |
