# Incremental skill proposal ("refresh skills" button)

Design + implementation record. Companion to `SKILL_PIPELINE.md`. This is the
groundwork that makes skill proposal safely re-runnable, so an instructor who
gets nothing (or a partial result) on first launch can just press a button and
have it correctly fill in the rest.

## The problem

Skill proposal was originally "run once per course, ever": the first time a
course had any skill row, all future runs no-oped. That's wrong for two real
cases:
1. A first launch that produced skills for only some modules (a flaky model
   call, an outage mid-run, or, historically, the truncation bug that only
   ever reached Module 1).
2. A module added mid-term after the course was already seeded.

In both, the instructor was stuck: the course "had skills," so nothing would
ever run again without manually deleting rows in the database.

## The design

**Track completion per module, not per course, and derive it from data
already written.** A module counts as "already proposed" if any skill row
exists with that `module_ref` for this course. Every proposed/approved skill
already carries its `module_ref` (from the per-module proposal work), so the
completion record is a natural byproduct, no new tracking table, nothing to
keep in sync.

On each run, `seed_course_skills`:
1. Groups live course content by module (unchanged).
2. Reads the set of `module_ref`s that already have skills for this course
   (`_already_proposed_modules`).
3. Processes only the modules present in the content but NOT in that set.

Consequences, all desirable:
- First run on a fresh course: every module is new → all processed.
- Re-run after a partial first run: only the un-covered modules process.
- Re-run when everything's done: processes nothing, returns
  `modulesProcessed: 0` cleanly (not an error).
- New module added later: only that module processes on the next run.

**Root content (`module_ref = None`) is tracked like any module** — proposed
once, then skipped, not re-run every time.

**Idempotent at the module grain.** The button is safe to press any number of
times; it only ever does new work. That's the property that lets other
features build on top without worrying about double-proposing.

## What this deliberately does NOT do (and why that's correct for now)

- It does not detect *changed* content within an already-processed module. If
  Module 2 already has skills and you edit a Module 2 lesson, re-running won't
  re-propose Module 2. Detecting intra-module content change would need
  content hashing/versioning, a real feature, out of scope here. The unit of
  incrementality is the module, which matches how instructors actually think
  about adding material.
- It does not delete or supersede skills when a module's content is removed.
  Skills are durable once created; cleanup is a separate, human-driven concern
  (the review UI's reject path, or the future curation screen).

## Response shape

```
{
  "skipped": false,              // true only when nothing new to do
  "modulesProcessed": 2,         // modules newly processed THIS run
  "modulesSkipped": 1,           // modules already covered
  "proposed": 5,                 // new 'proposed' skills staged for review
  "auto_approved": 1,            // matched an approved skill elsewhere, reused
  "flagged_possible_duplicate": 0
}
```

`modulesProcessed` + `modulesSkipped` = total modules in the course, always.
That invariant is a good demo-day sanity check.

## Endpoint

Unchanged from the prior batch: `POST /courses/{courseId}/skills/propose`
(instructor/admin). It already calls `seed_course_skills`, so it inherits the
incremental behavior automatically, no endpoint change was needed.
