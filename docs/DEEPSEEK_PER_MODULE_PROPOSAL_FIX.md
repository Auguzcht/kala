# DeepSeek instructions — skill proposal is now per-module, one call-site update needed

## The bug this fixes

Live demo evidence: a real 3-module CPE101 course only ever produced 5
proposed skills, and every single one matched Module 1's stated scope
(number systems, hardware/software basics). Nothing from Module 2 (embedded
computing) or Module 3 (system integration) appeared at all.

Root cause: `seed_course_skills()` took one joined string of the ENTIRE
course's content and made ONE model call, truncated to 24,000 characters.
For a real, content-rich 3-module course, Module 1's content alone likely
consumed that whole budget, Modules 2 and 3 never reached the model.

## What changed (backend, done and tested, 60/60)

`ai/skill_proposer.py`'s `seed_course_skills()` signature changed:

```python
# OLD
seed_course_skills(*, institution_id, course_id, course_content: str, module_ref=None)

# NEW
seed_course_skills(*, institution_id, course_id, content_items: list[dict])
```

It now groups `content_items` by module (reusing `lms/hierarchy.py`, the
same grouping `ingest_course()` already uses) and calls the model once PER
MODULE, each call only sees that module's own content. Each proposed skill's
`module_ref` is now set directly from the module that produced it, no more
waiting for the later ingest-time backfill inference. Response shape also
gained `modulesProcessed`, log/check this number, it should match the
course's actual module count.

## The one call-site change you need to make

Wherever `_seed_course_skills()` (or your launch-handler wrapper) calls into
this, in `lti/routes.py`, per the earlier BE-1 wiring, it currently builds a
single joined `course_content` string from `connector.get_content(course_ref)`
before calling `seed_course_skills`. That joining/truncation step should be
DELETED. Pass the raw `content_items` list straight through instead:

```python
# Before (delete this joining logic)
content_items = connector.get_content(course_ref)
content = "\n\n".join(i.get("body_or_description", "") for i in content_items)
seed_course_skills(institution_id=..., course_id=..., course_content=content)

# After
content_items = connector.get_content(course_ref)
seed_course_skills(institution_id=..., course_id=..., content_items=content_items)
```

Keep everything else about the wiring identical: still only for
instructor/admin, still gated on the course having no skills yet, still
wrapped in the same best-effort try/except so a proposal failure never
blocks the launch.

## Verify

1. Re-run against CPE101 (or any real multi-module course). Check the
   `modulesProcessed` count in the log/response, it should equal the actual
   number of top-level module folders in that course, not 1.
2. Check `GET /dashboard/{courseId}/skills/proposed`, you should now see
   skills whose wording clearly reflects Module 2 and Module 3 content too,
   not just Module 1.
3. Full backend suite should still be 60/60 after your call-site change,
   nothing else in the signature affects other tests.
