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
tests: [apps/web/src/components/shell/tests/tour.browser.mjs, apps/web/src/components/shell/tests/tour-route.test.mjs, apps/web/src/components/shell/tests/tour-anchors.test.mjs]
---

# Student and instructor walkthroughs

## Purpose
Orient students and instructors within the real workspace using guided highlights, local navigation and editable examples. Tours may point at a learning action but must leave grading, saving, sending, generation and retakes to the user's own explicit action.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Start/dismiss/restart their walkthrough; skip real learning actions | Have the runner rate/answer/send/start a test for them |
| instructor/admin | Walk through roster, triage, charts, skill review and learner record | Have the runner approve/reject/analyze/assign for them |
| tour runner | Navigate, open permitted UI panels/tabs, prefill an empty draft | Click persistence or model-call actions |

## Requirements

### TOUR-REQ-001: Offer a user-controlled walkthrough with local dismissal
- Rule: shell confirmation starts the tour; Got it and completion persist a role-specific per-user localStorage dismissal key. Header affordance can restart. Escape/overlay/close clears active step and leaves the user on the current page; no forced return. Active step/context lives in Zustand across shell routes.
- Acceptance: dismissed users do not see the first-use banner; finishing hides it; exit preserves navigation. Dismissal is local to browser/user, not synchronized across devices.
- Status: implemented
- Verified by: `apps/web/src/components/shell/tests/tour.browser.mjs`, local completion/dismissal, Back, Skip and Escape checks at 1440px/375px; synthetic APIs only. No hosted acceptance claim.

### TOUR-REQ-002: Build a fixed read-only plan before the first step
- Rule: Before step1, build the full role-specific plan using read-only GETs/counts-only reads and existing local state. Student outline is TOUR-REQ-007's twelve steps. Instructor outline order remains unchanged. Freeze N and step order for the run; x of N never jumps. Each step has target and fallback versions chosen without performing learning work. The Start tour control follows DESIGN.md C1: one pending indicator in that activated disabled control only.
- Rule: No bank-status wake, lesson generation/assignment, item claims/exposures or other write-capable read is allowed merely to plan or demonstrate the tour. Page navigation must not silently bypass this boundary through ordinary feature GET side effects. If a step cannot be demonstrated within owned paths without a write, stop and report; synthetic interception is not proof of production read-only behavior.
- Acceptance: Happy, empty and mixed course states have a complete fixed plan before step1. Existing counts-only reads create no learning/action writes. No step count/order change while walking, no submit/start/rating/Continue click, and zero mutating HTTP requests. Any unknown plan data leads to a same-page fallback, never fabrication or automatic content creation.
- Status: planned; APPROVAL-08 TOUR-2 supersedes the former prepared-topic/bank-status plan.
- Verified by: pending TOUR-2 source audit and desktop/mobile browser matrix.

### TOUR-REQ-003: Observe learning actions without performing them
- Rule: copy follows the current header, answering and results surfaces; Tutor covers history groups, rename/pin and file attach; Study explains end-of-deck replay versus Get new cards; Test explains saved results; Twin explains the independently paged evidence ledger and Load older activity, without implying lifetime statistics. Missing screens use their fixed-plan fallback rather than being created or silently skipped. Click steps are UI-only. The fixed plan explains learning actions without waiting for the student to perform them or dropping dependent steps. Prefill only writes to an empty textarea; never submits or overwrites a draft. Student must choose test creation/start, answer checks/questions, rate recall and send tutor text. Instructor tour highlights decision buttons without clicking them.
- Acceptance: Next/Skip never makes an answer, rating, retake, recommendation decision or tutor send request. Draft examples remain editable. Learner actions taken manually during the tour are normal real actions.
- Status: implemented
- Verified by: tour browser network spy plus route/config allowlist tests. Real components receive synthetic read responses; Next/Back/Skip/Escape and draft prefill issue zero mutating HTTP requests. Normal destination GETs can still write content/queue state (finding below).

### TOUR-REQ-004: Keep every step visible through a bounded fallback
- Rule: Every planned step has a target version and a centered no-highlight fallback on the same page, each with short copy. Wait until page loading ends, with a bounded wait; on timeout or absent target use fallback. No silent skips or toasts. An unexpected missing target emits only a dev-only console warning. Back works across pages without repeating a persistence action; x of N remains fixed.
- Rule: Highlight exactly the intended element with fixed padding, not an overbroad ancestor row/container. A step explicitly about a card or row targets that named card/row; button steps target only the button. The popover never obscures its own target and flips placement as needed. Each version uses at most two short sentences, no semicolons or material-availability wording. Keep keyboard and reduced motion.
- Acceptance: At375px/1440px in happy/empty/mixed seeded states, all12 student steps run in order, each has highlight or fallback, no toast/mutation, constant total and a highlight within the target's specified padding. Instructor audit applies the same rules without restructuring its outline. A truly removed target stops for coordinator definition/spec resolution, never deletion/rename of an anchor to silence the test.
- Status: planned; APPROVAL-08 TOUR-2 replaces silent-skip behavior.
- Verified by: pending TOUR-2 complete matrix; no partial merge if cutoff is missed.

### TOUR-REQ-005: Honor reduced motion and accessible orientation
- Rule: use Driver.js progress/close controls; scroll targets into view before positioning; disable smooth scrolling under prefers-reduced-motion. Copy describes topics/actions plainly and uses supportive instructor language.
- Acceptance: keyboard close exits; reduced-motion navigation uses auto scrolling; highlights/controls remain usable at desktop and 375px.
- Status: implemented
- Verified by: full reduced-motion walks and viewport bounds at 1440px/375px; keyboard Back and normal-motion Skip/Escape checks. Driver overlay now uses the brand-ink token. Screen-reader and live acceptance remain separate checks.

### TOUR-REQ-006: Preserve historical scope proof and current target bindings
- Rule: The seven accepted TOUR-REFRESH AST comparisons remain pinned to full accepted revision c3d6b6351f7adbfc6e8da1d43e371014473c8b74 and its pre-tour baseline3a6a0aab27a8212f77b83e96b26127d830a696ba. A committed two-sided normalized-AST checksum/attribute-count attestation makes that historical proof independent of local Git depth. If a verifier uses historical Git objects instead, absence fails clearly; never skip. Subsequent approved feature changes do not redefine the historical tour-only boundary.
- Rule: Independently enumerate every selector in current student/default/hub and instructor definitions, including wait/click/prefill targets and composite alternatives. Check its current component binding, including forwarded/dynamic IDs, exactly once at the rendering anchor. Preserve the current PracticePanel Study-spec comment. Runtime conditional visibility, absence/skip and route-specific uniqueness remain browser checks; a source binding is not proof of a visible DOM node.
- Acceptance: Keep all seven comparisons, no skip/only/todo or deleted anchors. Cover every current tour target, not just the original seven. Run old verifier before E3, new verifier before lanes and after merges; full desktop/mobile tour suite after integration must pass with zero mutating requests, reporting its new assertion count beside historical616. A disappeared target stops for explicit tour-definition/spec resolution.
- Status: planned
- Verified by: pending APPROVAL-08 E3 coordinator proof and integrated tour rerun.

### TOUR-REQ-007: Follow the twelve-step student outline
- Rule: Before starting, build these twelve steps in this order. Each has target/fallback copy and stable progress: (1) workspace Next up card, fallback “Kala suggests your next step here.”; (2) workspace Your twin at a glance; (3) Diagnostic start, fallback on Diagnostic “Your baseline check opens when its questions are ready. Until then, practice in Skills.”; (4) Skills first row, fallback “Skills appear here once your course is set up.”; (5) Lesson content and Continue, explain only and never click; (6) Lesson chat dock button; (7) Study Start studying button only and due count; (8) centered completion explanation, never start a deck: Go through these again replays this session and Get new cards checks new/due cards; (9) saved Test sets or New practice set card; (10) Tutor composer; (11) Tutor history/menu covering rename/pin/delete without performing them; (12) Twin evidence/Load older activity, fallback “Your learning evidence will show here as you practice.” Steps expected always present still retain an unexpected-absence fallback under TOUR-REQ-004.
- Rule: TOUR-2 submits required anchor locations first. U2/T2 add only owned attribute edits, coordinator merges those anchors before TOUR-2 rebases. A required anchor in a07-protected path stops for a named resolution. TOUR-2 owns tour shell/definitions and matching tour browser tests, never E3. U2 does not edit those tour paths. Instructor changes repair only violations of the shared rules, no outline restructure.
- Acceptance: Complete happy/empty/mixed student runs at375px/1440px, fixed twelve steps, exactly one target or centered fallback per step, no toasts or mutating requests, bounded loading wait, correct padding/placement and cross-page Back. Preserve E3 and current PracticePanel comment. All three states must pass before integration cutoff or no partial merge.
- Status: planned
- Verified by: pending APPROVAL-08 TOUR-2 anchor proposal, source no-write proof and complete browser matrix.

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

The earlier skip/GET-side-effect notes below describe the pre-TOUR-2 implementation. APPROVAL-08 requires fixed fallbacks and strictly read-only demonstration; those notes do not waive TOUR-REQ-002/004/007. Source integration remains pending.

- Missing/removed or hidden anchors are skipped; an empty class still walks through its available overview targets and omits learner-dependent steps.
- Optional results/Study-completion steps never create a session, submit answers or rate cards to reach their targets. The normal flow may skip them; the browse-step copy also explains the eventual end controls.
- Legacy availability can accept a cached ready lesson without five prepared questions, despite the unavailable message referring to five questions.
- Driver options do not independently prove accessibility; synthetic keyboard/mobile checks below pass, while screen-reader and live acceptance remain outstanding.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `docs/features/README.md:22` (tour never writes); `apps/web/src/components/shell/CourseShell.tsx:214` (bank status); `services/api/app/routers/bank.py:56` (wake); `services/api/app/routers/lessons.py:44` (GET generation) | Runner avoids explicit learning mutations, but normal reads/navigation can cause operational/content writes. | Define the invariant as no automatic learner evidence/actions, or add a read-only tour route mode; prove with network-spy acceptance. |
| `AGENTS.md` (tokens only); former TourRunner overlay literal | Previously hardcoded rgba. | Resolved by TOUR-REFRESH: brand-ink token with the existing 0.35 opacity; no shared palette change. |
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

## TOUR-REFRESH implementation verification

Initial base: `3a6a0aa`; post-DOCS-HYGIENE rebase base: `1d980e33a848559e01b229bd23408fd81fedc10f`. The current tour-only continuation supersedes the static-only tour acceptance limitation above for the synthetic cases listed here. All checks listed below were freshly rerun after that rebase; historical backend test runs are not upgraded and deployed/live acceptance is not claimed.

- `tour.browser.mjs`: **616 assertions passed**, student and instructor at 1440px/375px. Includes Back, Skip/Escape, concrete learner routes, visible targets, completed Diagnostic, missing material, empty roster/recommendations, editable empty-draft prefill and existing-draft preservation. Global network spy observed zero mutating requests and no file chooser was opened.
- `KALA_TOUR_REQUIRE_DOCS=1 node --test .../tour-route.test.mjs .../tour-anchors.test.mjs`: **11 passed, zero skipped**. Segment/wildcard boundaries and the UI click allowlist pass; TypeScript AST comparison proves exactly one added data-tour attribute and no other executable change in each of the seven anchor-only feature files against `3a6a0aa`. PracticePanel also retains the current Study citation from DOCS-HYGIENE.
- Retained Tutor/Diagnostic browser suite: **219 assertions passed**; frontend closeout suite: **110 assertions passed**; retained frontend Node checks: **21 passed**; Study renderer: **4 passed**.
- Web lint, typecheck and build passed. Existing warnings remain: 18 Fast Refresh warnings, route-generator circular dependency notice and build chunk-size warning. Screenshot inspection covered desktop Diagnostic and mobile Tutor history/instructor overview; artifacts are under `/tmp/kala-tour-refresh` (local only, not retained).
- Full matrix, exact commands and scope proof: `apps/web/src/components/shell/tests/TOUR-REFRESH-audit.md`.
- Documentation checker reports zero violations; its 18 tests pass. Configuration inventory check passes. A first concurrent retained closeout browser run timed out on keyboard Twin pagination; the unchanged standalone rerun passed all 110 assertions. The cause is not established and the original failure is retained in the audit.

The coordinator released the approved DOCS-HYGIENE merge; the rebase completed without conflicts, coexistence proof and fresh verification passed. Coordinator integration/review and live acceptance remain separate gates. No push, merge, deploy, hosted data repair or migration occurred here.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-27 | Define fixed read-only twelve-step student plan, centered fallbacks, bounded wait, no toasts and target geometry; instructor rules audit without restructure | APPROVAL-08 Amendment4, TOUR-2 | TOUR-REQ-002/003/004/007 |
| 2026-10-27 | Separate pinned historical AST scope attestation from exhaustive current tour-target checks before approved UI changes | APPROVAL-08 Amendment3, coordinator-only E3 | TOUR-REQ-006 |
| 2026-10-25 | Refresh current UI anchors/copy; skip unavailable conditional steps; add Back and synthetic zero-mutation acceptance | User-authorized TOUR-REFRESH | TOUR-REQ-001, TOUR-REQ-003, TOUR-REQ-004, TOUR-REQ-005 |
| 2026-10-25 | Specify per-step visible-target checks, bounded optional skips and remembered concrete learner routes before runner changes | TOUR-REFRESH continuation in the existing UI worktree | TOUR-REQ-001, TOUR-REQ-003, TOUR-REQ-004, TOUR-REQ-005 |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | TOUR-REQ-001 through TOUR-REQ-005 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | TOUR requirements above |
