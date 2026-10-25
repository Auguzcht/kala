---
feature: study
req_prefix: STUDY
owner_role: product owner
status: active
code:
  web: apps/web/src/features/flashcards/
  api: services/api/app/routers/flashcards.py
  worker: []
  db: []
tests:
  - services/api/tests/test_study_deck_approved.py
  - services/api/tests/test_membership_due_eligibility.py
  - apps/web/src/features/flashcards/tests/study-deck.test.mjs
---

# Study deck

## Purpose
Students recall course material with flip cards and self-ratings. Study advances the recall schedule; Test grades answers and supplies mastery evidence.

## Learning-surface boundaries

The skill hub is the canonical per-skill entry for Lesson, Study and Test, with Study browsing as its default. Skill choice belongs to the session/route, and module grouping keeps unassigned skills visible under Other topics. Legacy course-wide FlashcardDeck retains optional skill selection; do not silently remove it. Shared study presentation primitives are distinct from Tutor's conversation surface (TUTOR-REQ-011).

Practice/Test uses the existing practice router and Test browser. Bank-backed sets accept 5, 10 or 20 items; the legacy generated-set path remains bounded separately. A set groups delivery rather than replacing per-answer grading. Attempt/retake records and XP counting use immutable answer identity; repeated answers must not manufacture XP. [ADR-016](../../decisions/ADR-016-legacy-flashcard-xp.md) preserves the narrower counted-review versus evidence distinction. This boundary documents existing source and retained design rationale; it is not a complete Test specification or new acceptance claim.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Browse and review their own course cards | Change another student's schedule |

## Requirements

### STUDY-REQ-001: Counts reads have no side effects
- Rule: `GET /flashcards/{course_id}/deck?limit=0` returns stats and `cards: []`, without claiming, tracking, exposure writes, or spending the daily new-card allowance, in every mode.
- Acceptance: two consecutive counts requests create no schedule rows and preserve the remaining allowance.
- Status: implemented
- Verified by: services/api/tests/test_study_deck_approved.py

### STUDY-REQ-002: Resume served but unrated cards
- Rule: review serves active claimed cards with `reps=0` before any fresh top-up, without spending the daily new-card allowance again. Scheduled due cards retain priority. The shared Test/practice selector behavior is unchanged.
- Acceptance: leaving and reopening a deck re-serves the unrated card, even at the daily cap. All caught up requires no due, unrated, or eligible fresh card.
- Status: implemented
- Verified by: services/api/tests/test_study_deck_approved.py

### STUDY-REQ-003: Replay the completed session locally
- Rule: completion offers “Go through these again” and “Check for more cards”. Replay starts at card 1 with the same session cards and retains the posted-rating guard; it sends no new review POSTs. Label replay as practice without schedule changes. Check for more retains reload selection behavior. Empty copy distinguishes “All caught up” from “No cards yet”; show next due time if supplied.
- Acceptance: complete, replay, and rate the same cards without additional review POSTs; a separate action requests another deck.
- Status: implemented
- Verified by: apps/web/src/features/flashcards/tests/study-deck.test.mjs

### STUDY-REQ-004: Include eligible native flip cards in Study fresh selection
- Rule: Study fresh selection includes live native `flashcard` items alongside bank practice MCQs, subject to the existing claim and daily-cap rules. Only Study opts into `include_flashcards`; the shared selector defaults and Test/diagnostic/lesson MCQ pools remain unchanged.
- Rationale: membership and Study all already include native flip cards, but the old fresh selector excluded them. That could produce an empty review deck and “All caught up” while eligible cards remained. Matching Study membership fixes the same card-availability defect as STUDY-REQ-002.
- Acceptance: with an untracked bank MCQ and native flip card, Study fresh selection includes both; the existing non-Study regression still returns only the MCQ.
- Status: implemented
- Verified by: services/api/tests/test_study_deck_approved.py::test_STUDY_REQ_004_study_fresh_pool_includes_native_flip_cards; services/api/tests/test_study_deck_approved.py::test_STUDY_REQ_002_shared_due_and_test_pools_keep_original_behavior

### STUDY-REQ-005: Derive Preparing from actual Study bank availability
- Rule: for an empty course-wide deck, “Preparing” requires an actual visible skill with material whose bank is not usable. If all visible skill banks are ready, show “All caught up” when tracked cards exist or “No cards yet” when none exist, subject to the existing error, no-material, and cap states.
- Rationale: the old course-wide lookup returned no preparing skill when every bank was ready, then treated that missing result as preparing. This is the same empty-deck availability-classification boundary behind the caught-up-while-cards-remain defect: bank readiness and queue availability must support the displayed state. Correcting it makes the STUDY-REQ-003 empty-state distinction observable for a ready course.
- Acceptance: an empty course-wide deck with a ready bank renders “All caught up” for tracked cards and “No cards yet” for zero tracked cards, without “Preparing questions”.
- Status: implemented
- Verified by: apps/web/src/features/flashcards/tests/study-deck.test.mjs, “STUDY-REQ-005 empty ready course distinguishes caught up from no cards”

## API contract
| Method and path | Purpose | Auth | Notes |
| --- | --- | --- | --- |
| GET /flashcards/{course_id}/deck | Select review/all cards or read counts | Session | limit=0 is read-only; Study exposes answer labels and explanations |
| POST /flashcards/{course_id}/review | Self-rate first encounter per session | Session | Existing idempotency keys retained; replay makes no calls |

## Data
Read approved skills, live generated_items, courses, institutions, srs_state and skill_bank_state. Nonzero Study selection uses the existing tenant-scoped claim RPC and exposure/tracking writes. Counts use SELECT only. No SQL or RPC changes.

## AI usage (if any)
No provider calls for deck selection or replay. Existing optional tutor assistance is outside these requirements.

## Edge cases and known limits
Daily cap applies only to fresh review claims, not resuming unrated cards or Study all. Retired items and rejected skills stay excluded. Membership due badges count scheduled reviewed cards, independently of resumable unrated cards. No next-due field is added in this change. Live LMS and production smoke checks remain the maintainer's responsibility.

The component interaction tests depend on an external renderer fixture: matching `react` and `react-test-renderer` packages (verified with 19.2.8) resolved through `KALA_STUDY_TEST_DEPS`, plus Node's `--experimental-vm-modules` flag. The fixture is outside the repository; a clean checkout alone cannot run these tests until that fixture is supplied. The tests mock provider hooks and UI shells, so they do not verify browser layout or live HTTP integration. React emits a renderer deprecation warning. No dependency or shared test-harness change is included; integration harness work belongs to the coordinator.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Define minimal freeze scope before implementation | APPROVAL-01, Lane F and confirmed section 5 | STUDY-REQ-001, STUDY-REQ-002, STUDY-REQ-003 |
| 2026-10-24 | Make native flip-card fresh selection and its regression explicit | APPROVAL-02: retain the fix because eligible native cards could be omitted before an empty/caught-up result | STUDY-REQ-004 |
| 2026-10-24 | Make ready-course Preparing classification and its regression explicit | APPROVAL-02: retain the fix at the same Study empty-state availability boundary | STUDY-REQ-005 |
| 2026-10-24 | Record the external renderer fixture as a known verification limitation | APPROVAL-02; dependency and integration harness work stays outside this amendment | STUDY-REQ-003, STUDY-REQ-005 |

| 2026-10-25 | Retain existing mode/session rationale and replace obsolete launcher instructions with committed isolation and portable fixture commands | DOCS-HYGIENE; documentation only | Existing STUDY-REQ-001–005; no new REQs |

## Verification evidence

API checks now use the committed shared `services/conftest.py`; the old `run_study_checks.py` launcher was replaced during integration and must not be used. Run `uv run pytest` from `services/api`. The dedicated component test uses real React hooks with mocked provider hooks/UI shells; [current portable commands and external fixture setup](../../engineering/local-development.md#portable-frontend-checks) are retained in the truth layer. No package manifest changes are part of this spec amendment.
