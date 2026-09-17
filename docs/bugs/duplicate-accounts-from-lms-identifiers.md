# Bug: duplicate accounts from mismatched LMS identifiers

**Status:** fixed in `fa63769` + migration `0015`. Historical duplicate rows
remain — see "Still open" below.

## Symptom

An instructor's class roster showed a student as "0/10 skills measured ·
Not started · 0 evidence events · 0 attempts · never active" while that
student's account clearly had evidence — 149 events, five mastery rows, SRS
cards, quiz attempts, all produced by using the product.

The learner's work was real. The instructor was looking at a *different
account* for the same person.

## Root cause

`users.lms_user_id` is written from **two different Blackboard identifiers**
depending on which code path runs:

| Path | Identifier source | Example value |
|---|---|---|
| LTI launch | `payload["sub"]` — Blackboard's LTI subject claim | `2aca8e5459054620993530550b5f0a93` |
| Roster sync | connector's REST `userId` | `_10_1` |

`upsert_user` conflicted on `(institution_id, lms_user_id)`, so the two paths
created **two rows for one person**:

- the **launch-created** row carried the evidence (all the real work)
- the **roster-created** row carried the enrollment — and therefore was the
  one the instructor saw

Confirmed live: 4 such pairs. The worst had 149 evidence rows stranded on the
account no staff surface could reach.

## Fix

`resolve_user` replaces `upsert_user` on **both** paths (the split runs in
both directions — whichever path runs second must find the first's row).
Resolution order:

1. **Alias lookup** — `lms_identity_aliases` (migration `0015`) maps any LMS
   identifier Kala has seen to a user. Exact and stable, indifferent to which
   identifier form arrived.
2. **Email match** — both paths already fetch email, and it matched exactly in
   every observed duplicate pair, so it is a good discovery signal.
3. **Create**, keyed on `lms_user_id`.

### Two hard requirements

1. **The `lms_user_id` fallback stays.** Email is not guaranteed present on an
   LTI launch and is not guaranteed unique. Resolution must not depend on it.
2. **The alias is written on every successful resolution**, not only for new
   users. That is what lets step 1 take over on the next launch, and it
   back-fills the *other* identifier for a user found by email.

Both are pinned by tests in `services/api/tests/test_lti_launch.py`.

### Why email is not the permanent key

Email is mutable, and an address change must not fork an account. It is a
**discovery** signal only; the alias row is what makes resolution durable. The
alias table is populated by **observation** rather than computed, because
whether Blackboard documents a relationship between `sub` and REST `userId` is
exactly what is not known — and auth code should not rest on that guess.

## Verification (live, against the real database)

Round-trip on a real enrolled student:

```
BEFORE   33 users · target lms_user_id=_13_1 · 0 aliases for the test sub
CALL     resolve_user(sub=<unseen>, email=<match>)   -> resolved to target
AFTER    33 users   (NO twin created)
         alias written for the new sub (source=email_match)
SECOND   resolve_user(sub=<same>, email=None)        -> SAME user
         ^ proves the alias path works with no email at all
```

Synthetic test alias removed afterwards; 57 aliases remain (35 identifier + 22
email).

## Still open — the historical pairs

The fix prevents **new** splits. It does not repair the 4 existing ones, for a
structural reason:

- **`evidence_events` is append-only by trigger** (deliberate — it is the
  research dataset and audit trail, tamper-resistant even for service_role).
  The 149 stranded events therefore **cannot be re-pointed** to the enrolled
  account. This was discovered the hard way: the merge script's first PATCH was
  rejected with `P0001: append-only table: UPDATE not allowed on
  evidence_events`, before anything moved.
- A launch now resolves those students by email to the **oldest** account
  (`_user_by_email` picks oldest, deterministic). For Hanna that is the
  *enrolled* one — correct for future work, but her pre-existing evidence stays
  orphaned, so the instructor still sees `0 evidence events` until new activity
  lands.

**Decision needed:** leave those 4 pairs as they are (they are test accounts,
the fix is forward-correct, and the events are evidence of the original split),
or repair them some other way. Deleting the orphaned events is possible but was
deliberately not done — they are the record of how the split happened.

## Reset is separate

Clearing Hannna's test data is its own decision, deferred until after the
account state is understood. Nothing here predetermines it.

## Related

- Migration: `packages/db/migrations/0015_lms_identity_aliases.sql`
- Repair tool: `scripts/merge_duplicate_user.py` (dry-run by default; blocked
  by the append-only trigger on the one table that matters most)
- Tests: `services/api/tests/test_lti_launch.py` — 4 regression tests
