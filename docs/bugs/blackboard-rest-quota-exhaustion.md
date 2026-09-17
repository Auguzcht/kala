# Blackboard REST quota exhaustion (dev instance, 2026-09-17)

## What happened

Every LTI launch on the dev instance failed, because Kala had spent the
Blackboard Learn REST quota (10,000 requests) faster than it refills. Confirmed
by raw curl against the live instance:

```
HTTP/1.1 429
Retry-After: 20807s
X-Rate-Limit-Limit: 10000
X-Rate-Limit-Remaining: 0
{"status":429,"message":"Unauthorized"}
```

`20807s` is roughly 5.8 hours. Until that window resets, Blackboard is
unreachable for live testing — no launch, no roster, no ingest.

## Root cause: three compounding leaks

None of these is a bug in isolation. Together they turn ordinary dev testing
(repeated relaunches of the same course) into a quota fire.

1. **`resolve_course_ref` was uncached.** It called
   `GET /courses/externalId:{id}` on every launch. The `courses` table stored
   the *resolved* internal id but never the *external* id it was resolved from,
   so a local lookup was not merely missing — it was impossible.

2. **Roster sync and skill seeding ran on every instructor launch,** by design
   and documented as such in their own docstrings ("self-heals on a timescale of
   minutes, not migrations"). Correct for production, ruinous for a demo
   session: each reload repaid a full paginated roster pull plus a content walk.

3. **No 429 handling anywhere.** `resp.raise_for_status()` threw a generic
   `HTTPStatusError` straight through, so once the quota tripped every launch
   failed loudly with raw Blackboard text and no retry-after information.

## Fixes

**Fix 1 — resolve once, remember it.** Migration `0016_lms_course_resolution_cache.sql`
adds `courses.lms_course_external_id` (nullable, partial unique index on
`(institution_id, lms_course_external_id)`). The launch now looks the course up
locally first (`db.course_by_lms_external_id`) and only calls Blackboard when
nothing matches, persisting the external id on that path so the next launch
takes the local route.

**Fix 2 — cooldown the per-launch syncs.** Same migration adds
`last_roster_sync_at` and `last_skill_seed_at`. A launch inside the 600s window
skips the corresponding pull and logs why; the timestamp is written only on
*success*, so a skip or a failure never blocks a real retry. The self-healing
contract is intact — a genuine roster change still reconciles within a class
period — but a relaunch burst no longer repays the full cost each time.

**Fix 3 — fail once, informatively.** `_check_rate_limit` runs before every
`raise_for_status` and raises `BlackboardRateLimitedError` (carrying
`Retry-After`). No blind retry: a 429 with `X-Rate-Limit-Remaining: 0` means an
immediate retry is guaranteed to fail and spends another request against a zero
quota. The launch route catches it and returns a 502 naming the retry-after.
Every successful response logs `X-Rate-Limit-Remaining`, warning below 500 —
the early signal whose absence let this arrive unannounced.

## Gotcha worth remembering

Blackboard sends `Retry-After: 20807s` — **with a trailing `s`**, which the RFC
does not define. A bare `int(float(...))` parse rejects it and silently
downgrades the error message to "when the window resets". `_retry_after_seconds`
matches the leading digits instead, and a test pins the exact live header.

## Still to do

- **Apply migration 0016.** Fixes 1 and 2 are inert without it. The code is
  written to fail *open* until then: `course_by_lms_external_id` treats an
  unmigrated column (PostgREST 400) as "not found" and falls back to REST,
  and `touch_course_sync_timestamp` swallows a write failure. A missing
  migration is a slow launch, never a dead one — but the caching does not
  engage until the column exists.
- **Confirm the quota has reset** before attempting a live launch.
- **Live verification at scale.** The mocks pin the mechanics; the claim that
  a relaunch burst no longer burns quota needs one real session after the
  window resets, watching `X-Rate-Limit-Remaining`.
