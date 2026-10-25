---
feature: gamification
req_prefix: GAME
owner_role: product owner
status: active
code:
  web: apps/web/src/features/gamification/
  api: services/api/app/routers/gamification.py
  worker: []
  db: [packages/db/migrations/0001_init.sql, packages/db/migrations/0027_item_reviews.sql, packages/db/migrations/0031_atomic_practice_submit.sql, packages/db/migrations/0034_attempt_aware_practice.sql]
tests:
  - services/api/tests/test_xp.py
  - services/api/tests/test_learn_routes.py
---

# Evidence-based rewards

## Purpose
Kala rewards learning activity through derived XP, UTC-day streaks and mastery badges. There is no client-writable reward balance; the summary can be recomputed from saved outcomes.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated user | Read their own reward summary for a course | Set XP, streak or badge values |
| grading service | Persist authoritative answer/review outcomes | Accept a client reward amount as truth |

## Student read admission

The reward-summary GET follows [AUTH-REQ-007](../lti-auth/README.md#auth-req-007-require-existing-course-enrollment-on-student-reads) before computing reward data. Enrolled XP, streak and badge calculations remain unchanged; the guard introduces no reward writes. Admission implementation/verification is pending the approved follow-up; this requirement is not a live acceptance claim.

## Requirements

### GAME-REQ-001: Derive XP without double-counting practice reviews
- Rule: sum saved practice_answer_results.xp_awarded; add counted item_reviews at 2 participation XP plus 10 for good outcome, excluding quiz reviews whose idempotency key already appears in saved practice answers. Other evidence (excluding practice/flashcard types) receives 2 plus 10 when correct. No balance writes on summary reads.
- Acceptance: re-reading summary cannot earn XP; a practice answer and its matching counted quiz review contribute once.
- Status: implemented
- Verified by: `test_xp.py::test_xp_rewards_correct_over_attempts`, `test_xp_uses_saved_practice_xp_and_does_not_double_count_quiz_reviews`; practice repeat-submit coverage in `test_learn_routes.py`.

### GAME-REQ-002: Compute streaks from consecutive UTC evidence days
- Rule: count unique evidence calendar days backwards from today, or yesterday if today is unfinished; no activity on either day yields zero. Multiple events on one day count as one day.
- Acceptance: missing today preserves yesterday's streak; a gap breaks it; empty history is zero. Calendar semantics are UTC, not browser time.
- Status: implemented
- Verified by: `test_xp.py::test_streak_counts_consecutive_days_up_to_today`, `test_streak_survives_an_unfinished_today`, `test_streak_zero_when_no_recent_activity`, `test_streak_empty`.

### GAME-REQ-003: Award badges only for approved skills
- Rule: skill badges are proficient at estimate >=0.7 and mastered at >=0.85; Bloom badges require every approved skill at that level to be at least 0.7. Missing mastery does not qualify.
- Acceptance: rejected/unmeasured skills cannot award a badge; a partly proficient Bloom level has no Bloom badge.
- Status: implemented
- Verified by: `test_xp.py::test_badges_award_skill_and_bloom_tiers`; static `learn/xp.py::_badges` approved-skill filter. Twin band naming differs, as recorded below.

### GAME-REQ-004: Announce newly observed rewards without replaying old achievements
- Rule: first real summary response establishes the UI baseline. Later badge-count increases show Badge earned; later streak increases animate the flame. Digits render statically under reduced motion. Loading shows the shared Spinner labeled Loading your progress; absent data after loading hides the compact instrument.
- Acceptance: opening a workspace with existing badges/streak does not toast them as new; subsequent increases update the top bar.
- Status: partial
- Verified by: static `GamificationSummary.tsx` refs/effects; no committed component regression test or browser/reduced-motion verification in this lane. Flame imperative animation is not explicitly gated by reduceMotion in this component.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /gamification/{course_id}/summary | Own xp, attempts, correct, streakDays, badges | Session | Read only; malformed ID 404; no XP mutation endpoint |

`attempts`/`correct` summarize non-practice evidence plus counted reviews; practice XP is separately summed from saved answer snapshots. These counters must not be described as a complete count of every historic practice submission.

## Data
Read evidence_events, item_reviews, practice_answer_results, approved skills and mastery_state. Summary writes nothing; authoritative writers are the learning routes/RPCs. Evidence/mastery RLS allow self/course staff/institution admin; review/result tables use owner-oriented policies from their migrations. The API uses service-role DB access: the summary's event/review/result queries filter user/course but omit an explicit institution filter; the badge queries do include it. The audited baseline lacked student course-enrollment enforcement; AUTH-REQ-007 now requires the existing admission guard before this read, with implementation verification pending.

## AI usage (if any)
None. Reward arithmetic and badge decisions are deterministic. Generated content or tutor answers earn nothing merely by being viewed.

## Edge cases and known limits
- Badges are derived, not permanent awards: skill rejection or a falling estimate can remove them.
- UI detects count growth, not a full identity/tier diff. A badge tier upgrade without a count increase does not trigger the toast.
- Streak uses evidence_events; a self-rated Study review that writes no evidence does not itself extend the streak.
- Summary reads have no explicit pagination; no large-history completeness claim is made.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/learn/xp.py:35` (badge constants/comment); `services/api/app/twin/summary.py:13` (band thresholds) | The comment says badge thresholds match twin bands, but they differ. | Confirm intentional reward tiers or align them in a separately authorized behavior change. |
| `apps/web/src/features/gamification/components/GamificationSummary.tsx:41` (flame increase); `apps/web/src/features/gamification/components/GamificationSummary.tsx:91` (reduced-motion digit branch) | Numeric motion is gated, but the imperative flame call has no local reduced-motion check. | Verify the primitive/browser behavior, then add a gate if needed in a UI-owned task. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked XP/streak/badge arithmetic and the compact UI against integrated source. Loading now renders the shared Spinner labeled Loading your progress; absent settled data still hides the instrument. GAME-REQ-004 and current source anchors reflect that observation; reduced-motion/badge-count limitations are retained. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Require existing enrollment admission on inventoried student GETs; preserve staff, mutations and enrolled processing | APPROVAL-07 Amendment 7; coordinator spec before follow-up implementation | AUTH-REQ-007; WI-26 |
| 2026-10-25 | Write full source-backed feature spec; identify limits and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | GAME-REQ-001 through GAME-REQ-004 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | GAME requirements above |
