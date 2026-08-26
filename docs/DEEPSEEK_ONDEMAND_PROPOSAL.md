# DeepSeek instructions — on-demand skill proposal (no relaunch needed) + refresh button

## Backend, done and tested (62/62)

New endpoint: `POST /courses/{courseId}/skills/propose`, instructor/admin
only. Fetches content fresh from the connector and calls
`seed_course_skills` directly, same pipeline the launch handler already
uses, just callable whenever, not only as a side effect of a fresh
Blackboard launch.

**Important, same idempotency as before:** if the course already has ANY
skill rows (approved or proposed), this is a no-op, same guard as always.
This is for triggering the *first* proposal run on demand, not for
re-running proposal after content changes, that's a different, unbuilt
feature (see "Not built" below).

## What immediately unblocked today's testing

If a course already has skill rows from before the per-module fix landed
(the "5 skills, all Module 1" bug), calling this new endpoint on that course
will still no-op, the guard doesn't know those rows are stale, it only knows
rows exist. Delete the existing rows for that course in Supabase first, then
call the endpoint (or relaunch, either works now, they hit the identical
code path).

## Frontend — one small addition to the SkillReviewPanel

Add a "Re-run skill proposal" button near the panel header (only meaningful
when the panel is otherwise empty/hidden, i.e. no proposals pending and the
instructor wants to trigger the first run without waiting for/faking a
relaunch). On click: `POST /courses/{courseId}/skills/propose`, then
refetch `GET /courses/{courseId}/skills/proposed` to populate the panel.

Show the response's `modulesProcessed` count somewhere visible after the
call completes (a toast or inline note is enough, e.g. "Processed 3
modules, 8 proposals ready for review"), that number is the demo-day sanity
check that every module was actually seen, not just the first one.

If the call returns `{"skipped": true, ...}` (course already has skills),
show a clear message like "This course already has skills, nothing to
propose" rather than silently doing nothing, an instructor clicking a
button that appears to do nothing is worse than one that explains why.

## Not built (real gap, worth flagging, don't build now)

There's no way yet to re-run proposal against a course that already has
skills but has since gotten NEW content (a module added mid-term, say).
The idempotency guard treats "any skills exist" as "fully done forever."
A real incremental version would need to track which content has already
been proposal-processed and only run against what's new, that's meaningfully
more design than a button, sequence it as a real post-Sept-1 feature, same
bucket as the module/skill curation screen already deferred, not something
to improvise under deadline pressure.
