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
- Rule: review serves active claimed cards with `reps=0` before any fresh top-up, without spending the daily new-card allowance again. Scheduled due cards retain priority. Native flip cards and bank MCQs are both eligible in Study. The shared Test/practice selector behavior is unchanged.
- Acceptance: leaving and reopening a deck re-serves the unrated card, even at the daily cap. All caught up requires no due, unrated, or eligible fresh card.
- Status: implemented
- Verified by: services/api/tests/test_study_deck_approved.py

### STUDY-REQ-003: Replay the completed session locally
- Rule: completion offers “Go through these again” and “Check for more cards”. Replay starts at card 1 with the same session cards and retains the posted-rating guard; it sends no new review POSTs. Label replay as practice without schedule changes. Check for more retains reload selection behavior. Empty copy distinguishes “All caught up” from “No cards yet”; show next due time if supplied.
- Acceptance: complete, replay, and rate the same cards without additional review POSTs; a separate action requests another deck.
- Status: implemented
- Verified by: apps/web/src/features/flashcards/tests/study-deck.test.mjs

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

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Define minimal freeze scope before implementation | APPROVAL-01, Lane F and confirmed section 5 | STUDY-REQ-001, STUDY-REQ-002, STUDY-REQ-003 |

## Verification evidence

`run_study_checks.py` disables dotenv and socket connections and generates an ephemeral signing key for mocked launch tests. Run it with an empty environment as documented in its module docstring. The dedicated component test uses real React hooks with mocked provider hooks/UI shells; its header documents the isolated renderer dependency and command. No shared test harness or package manifest is changed.
