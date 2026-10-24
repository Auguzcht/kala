---
feature: twin
req_prefix: TWIN
owner_role: product owner
status: active
code:
  web: apps/web/src/features/twin/
  api: services/api/app/twin/summary.py
  worker: []
  db: []
tests: [apps/web/src/features/twin/tests/presentation.browser.mjs]
---

# Twin presentation amendment

## Purpose

This focused WI-22 amendment defines readiness-number legibility and bounded evidence browsing for student and instructor views. The broader Twin specification remains incomplete under WI-08; mastery/readiness calculations and evidence history contracts are unchanged.

## Actors and permissions

| Actor | Can | Cannot |
| --- | --- | --- |
| Student | Browse the evidence returned for their own twin | Read another student's record |
| Instructor with existing course access | Browse a learner's returned evidence and readiness through existing authorized routes | Gain new course or learner access through this presentation amendment |

## Requirements

### TWIN-REQ-001: Make readiness values legible inside large rings

- Rule: The shared MasteryRing uses a prominent 48px token-sized, monospaced center value for readiness rings of 128px or more, including the student's 176px board-readiness ring and instructor's 144px readiness ring. Preserve the compact 12px value in 56px skill rings. Keep existing values, null state, fill calculation and motion semantics; reduced motion renders a static number. Zero and 100 must fit without clipping. Expose the value and band with the ring's accessible label.
- Acceptance: Student and instructor readiness centers use the same 48px number style; compact rings retain their original density; null/0/100 render correctly with motion allowed and reduced.
- Status: implemented
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### TWIN-REQ-002: Keep Focus area heading plain

- Rule: Remove the decorative icon next to the Focus area heading in shared TwinBody. Preserve its text, skill, mastery band and practice action, including the instructor twin drill-down.
- Acceptance: Focus area has no heading icon and retains the underlying data/action.
- Status: implemented
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### TWIN-REQ-003: Page the evidence ledger consistently

- Rule: The shared EvidenceLedger shows ten returned events per page in the existing server order, using Kala's Pagination primitives at the same default 40px control size as the instructor roster. Display the current range and label the total as recent events, not lifetime history. Show page controls only when multiple pages exist; handle empty/one-page lists. The student twin, instructor twin drill-down and learner record use this same component.
- Rule: Page changes replace rows immediately without animating an entire page as new evidence. New events arriving on the current page retain the existing short reveal, disabled by reduced motion. Keep pagination controls keyboard accessible, explicitly disable endpoints, clamp the selected page when the returned list shrinks, and fit mobile widths without horizontal overflow. Use the existing pageWindow helper on larger screens and compact the visible number links on small screens without shrinking controls.
- Acceptance: Ten rows at most are shown; next/previous/numbered/keyboard navigation retains order and stable controls; final-page ranges and disabled endpoints are correct; empty lists and shrinking data are safe at 375px and desktop widths. Both instructor/student views inherit the behavior.
- Status: implemented
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

## API contract

No API, schema, authorization or query change. Existing student Twin response contains at most 20 recent events. The instructor learner-record implementation reads at most 200 events internally for its statistics, but serializes only the latest 25 into its evidence array; the instructor Twin drill-down uses the Twin response. Pagination navigates the returned array and does not imply access to all historical evidence. Full-history server pagination is separate work. The earlier 200-row response description confused the internal read limit with the serialized ledger window; the finalization handoff records this correction.

## Data

No new persistence. Readiness and evidence remain server-owned; only the current presentation page is local UI state. Evidence remains append-only and is never edited or deleted by pagination.

## AI usage

None added.

## Edge cases and known limits

Long skill names, mobile widths, empty/one-page lists, list shrinkage, null/0/100 readiness and reduced motion are part of done. Focus and pagination must remain usable without pointer input. No hosted mutation or deployment is authorized by this amendment.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Define prominent readiness numbers, plain Focus area heading and shared ten-row ledger pagination before implementation | Fred's direct WI-22 visual/pagination request for student and instructor views | TWIN-REQ-001, TWIN-REQ-002, TWIN-REQ-003 |
| 2026-10-25 | Correct the observed instructor ledger response window to 25; distinguish the internal 200-event statistics read | Final UI/UX handoff source trace of cohort.learner_record; no runtime or intended-behavior change | TWIN-REQ-003 |
