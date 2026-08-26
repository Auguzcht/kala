# Skill proposal pipeline (HITL)

Scoped working doc. Companion to `UI_AND_MODULES.md`. Describes the
AI-proposed, human-reviewed, institution-deduped skill pipeline shipped in
migration `0007` + `ai/skill_proposer.py`.

## Why this exists

MMCM has run a fully-digital Blackboard since 2018: hundreds of courses, many
shared or reused across departments (an engineering course and an AEC course
both covering Boolean logic; the same core course taught by several colleges).
Hand-mapping a skill graph per course through a CEA spreadsheet does not scale
to that catalog, and it also undercuts the product story (an "AI-enabled
learning-intelligence platform" whose skills are typed in by hand is a
contradiction).

The consistent asset is that the courses already exist, fully built, with real
materials, and are heavily reused. So: let AI seed the skill graph from the
content that's already there, with tight guardrails, and keep a human in the
loop to approve before anything counts.

## The three concepts (kept distinct on purpose)

- CONTENT — "what is taught" (`content_items`, chunked + embedded on ingest)
- SKILLS — "what a student should be able to DO" (`skills`, now proposable)
- EVIDENCE — "what student behavior demonstrates it" (`evidence_events`)

Bloom describes the cognitive demand of a SKILL. It is metadata on the skill,
not a per-student value that drifts like mastery. (Mastery lives in
`mastery_state`; the two are different dimensions.)

## The pipeline

1. **Propose** — one reasoning-tier model call per course reads the course's
   ingested content and proposes a small set of canonical, assessable skills,
   each with a Bloom level and a blueprint weight. Guardrails live in the
   prompt AND are enforced in code (`_parse_proposals` drops anything vague or
   malformed): observable/assessable wording, a cognitive verb per skill,
   in-proposal dedup, few-but-good (3-6 per module), weights clamped 0.5-2.0.

2. **Dedup across the institution** — before writing a proposed skill, embed it
   and search every ALREADY-APPROVED skill in the institution (any course) via
   the `match_skills` pgvector function. Three bands:
   - `>= AUTO_MATCH (0.92)` — same skill, already vetted elsewhere. Reuse its
     name/bloom/weight, write straight to `approved`, point
     `canonical_skill_id` at the origin. No human needed.
   - `>= REVIEW_HINT (0.82)` — likely duplicate. Create as `proposed` with a
     "possible duplicate of X" note for the reviewer.
   - `< REVIEW_HINT` — genuinely novel. Create as `proposed`.

3. **Human-in-the-loop** — anything `proposed` waits for a human. Only
   `approved` skills feed the twin, heatmap, diagnostic, practice, flashcards
   (every learner-facing read now filters `status = approved`). Review is via
   `GET /dashboard/{course}/skills/proposed` +
   `PATCH /dashboard/{course}/skills/{id}/review` (approve/reject, with
   optional inline edits), or straight in Supabase for the demo.

## The leverage

The first course through needs real review. By the Nth shared course, most
proposals auto-match already-approved skills, so the review burden shrinks as
the catalog fills in. This is the whole reason the dedup is institution-wide
and not course-scoped.

## Trigger

Fires on instructor/admin launch when the course has no skills yet, same
non-blocking, best-effort posture as roster sync (a proposal failure must
never block a launch). By the time a student launches, proposals/matches are
already staged. (Wiring into the launch handler is the one backend TODO, see
DeepSeek instructions.)

## Schema (migration 0007, additive)

On `skills`: `status` (proposed/approved/rejected, default approved so
existing hand-entered rows stay live), `embedding vector(1024)`,
`canonical_skill_id` (origin of an auto-matched reuse), `proposed_source`
(module/dup-hint), `reviewed_by`, `reviewed_at`. Plus the `match_skills`
pgvector function. Nothing that already reads `skills` changed shape; the
learner-facing reads just gained a `status = approved` filter.

## What is NOT built yet (deferred, same bucket as module curation UI)

A polished in-app review screen. For the demo, reviewing in Supabase's table
editor (flip `status`, edit name/weight inline) is sufficient. The real review
UI is post-Sept-1 work and should be designed together with the module
curation screen from `UI_AND_MODULES.md` §3 — they're the same surface.
