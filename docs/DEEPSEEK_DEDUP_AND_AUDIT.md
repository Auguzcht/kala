# DeepSeek instructions — in-batch dedup + auto-match auditability/detach

Backend done and tested (79/79). Two related improvements, both grounded in
what was seen live (two near-duplicate number-system skills from one run, and
the question of what happens when cross-course matches inherit wording tuned
for a different course). Read this whole file before the frontend work.

## The design decision (why in-batch and cross-course are treated DIFFERENTLY)

- IN-BATCH duplicates (two proposals from the SAME run): FLAG, never
  auto-collapse. Both are unvetted; picking a winner between them is a review
  decision that belongs to the human. Each side gets a "possible duplicate of
  'X' (this batch)" note; both survive for the instructor to merge/pick.
- CROSS-COURSE match (a proposal resembles an ALREADY-APPROVED skill in
  another course): still auto-approves at >= AUTO_MATCH (0.92). That reuse is
  the scaling win and it's earned, the other side was human-vetted. BUT it's
  now auditable (proposed_source records what it matched) and reversible (an
  instructor can detach it to tune for their course).

The asymmetry is the point: unvetted-vs-unvetted → human decides;
fresh-vs-already-vetted → reuse by default, human can override.

## New/changed backend (already in this repo, no action needed except FE)

- `ai/skill_proposer.py`: two-phase per module (embed all → flag in-batch
  dups → write). New `flagged_in_batch_duplicate` count in the response.
  Auto-matched rows now carry an auditable `proposed_source`
  ("auto-matched to 'X' (sim 0.97)"). DeepSeek's insertFailed resilience is
  preserved.
- `GET /dashboard/{courseId}/skills/auto-matched`: lists live skills that were
  inherited via cross-course match (canonical_skill_id set), so the instructor
  can SEE the reuse instead of it being invisible.
- `PATCH /dashboard/{courseId}/skills/{skillId}/detach`: turns an auto-matched
  skill back into a course-local 'proposed' skill (clears canonical_skill_id,
  clears reviewed_by/at). It re-enters the normal review flow and stops
  feeding learner surfaces until re-approved.

## Frontend work

### 1. Show in-batch dup hints in the existing review panel
The proposed-skills list already renders `proposed_source`. In-batch dups now
put "possible duplicate of 'X' (this batch, sim N)" there (possibly alongside
an approved-match hint, joined with "; "). Surface it prominently, same as the
existing dup hint, this is the instructor's cue that two rows in the SAME list
might be the same skill. No new endpoint; it's already in the data.

### 2. New "Auto-matched from other courses" section
A small collapsible section on `/class`, fed by
`GET .../skills/auto-matched`. For each: name, Bloom, weight, module, and the
`proposed_source` (what it matched). Each row gets a "Tune for this course"
button → `PATCH .../detach`, then refetch both the auto-matched list and the
proposed list (the detached skill moves from one to the other). Explain it in
one line: "These skills were reused from another course. Tune one to make a
course-specific copy for review."

Keep both bespoke/task-driven per UI_AND_MODULES §2. Hide each section when
empty.

## What NOT to do
- Do NOT auto-merge in-batch duplicates. Flag only. The whole design rests on
  the human making that call.
- Do NOT make detach destructive to the ORIGIN skill in the other course, it
  only ever affects THIS course's row (the endpoint's filters enforce that).
