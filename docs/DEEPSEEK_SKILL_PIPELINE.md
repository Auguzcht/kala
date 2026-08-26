# DeepSeek instructions — skill pipeline wiring + review UI

The backend for the HITL skill pipeline is built and tested (40/40 passing).
See `SKILL_PIPELINE.md` for the design. Your job is the wiring and the
frontend. Read `SKILL_PIPELINE.md` first.

## Prereqs (do first, in order)

1. Apply migration `0007_skill_proposals.sql` to the live Supabase project.
   Confirm the `match_skills` function and the new `skills` columns exist.
   (Also confirm `0005` and `0006` were applied — if the learn loop or module
   fields are missing, an earlier migration was skipped.)
2. Restart the API after migrating (settings + schema are read at startup).

## Backend — one wiring task (BE-1)

The proposer exists (`ai/skill_proposer.py`) but nothing calls it yet. Wire
`seed_course_skills` into the LTI launch handler in `lti/routes.py`, right
next to where roster sync (`_sync_roster`) is already called, and following
the exact same pattern:

- Only when `app_role in ("instructor", "admin")` AND a course is resolved.
- Only when the course has no skills yet (the function already guards this,
  but gate the call too so you don't fetch content pointlessly).
- Pull the course content (the ingest path already knows how — reuse
  `connector.get_content(course_ref)` and join the chunk/body text into one
  string to pass as `course_content`).
- BEST-EFFORT: wrap in try/except, log and continue on any failure. A proposal
  error must NEVER block the launch (same contract as roster sync — see
  masterplan §17). Do not await anything that can hang the 302.
- Add a launch-level test mirroring the roster-sync tests: an instructor
  launch on a course with no skills calls the proposer; a student launch does
  not; a proposer exception still returns 302.

Do NOT change any of the learner-facing skill reads — they already filter
`status = approved` (twin, diagnostic, practice, flashcards, heatmap). Don't
add the filter twice.

## Frontend — review surface (FE-1), minimal for the demo

Two endpoints exist:
- `GET /dashboard/{courseId}/skills/proposed` → `{ proposed: [{id, name,
  bloom_level, blueprint_weight, proposed_source}] }`
- `PATCH /dashboard/{courseId}/skills/{skillId}/review` with body
  `{ status: "approved" | "rejected", name?, bloom_level?, blueprint_weight? }`

Build a lightweight instructor-only review panel on the instructor dashboard
(`/class`): a list of proposed skills, each showing name, Bloom level, weight,
and the `proposed_source` note (which may say "possible duplicate of X" — show
that prominently, it's the reviewer's main signal). Each row gets Approve and
Reject; Approve may optionally edit name/bloom/weight inline before sending.
After a decision, remove the row from the list.

This is a WORKFLOW surface, not record CRUD — build it bespoke per
`UI_AND_MODULES.md` §2, do not reach for a generic form renderer. Keep it
simple; it does not need to be the polished long-term curation screen (that's
deferred and will merge with module curation later). A plain reviewable list
with two buttons is the Sept 1 bar.

Guard the panel to instructor/admin (the endpoints already 403 others, but
don't render it for students).

## What NOT to do

- Don't build the polished long-term curation UI now (deferred).
- Don't let proposed skills appear anywhere a learner sees (they're already
  filtered server-side; just don't add a new client read that ignores status).
- Don't make the launch wait on skill proposal. Best-effort, non-blocking.
