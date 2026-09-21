# services/api/app/routers/diagnostic.py — make /ingest enqueue, not walk

This is the change that takes the walk off the request-response door. The
current `ingest_course` (around line 176) calls `connector.get_content(...)`
synchronously, then stores + embeds inline — that is the 31.8s walk that times
out at the 30s wall. Replace the walk-and-store with an enqueue.

## What to keep

- The `_course_ref(...)` / auth / `require_valid_course_id` guard — unchanged.
- `POST /{course_id}/content/upload` (staff upload) — **unchanged**. That path
  hands bytes straight to store+embed and never walks the tree, so it was never
  the problem. Leave it exactly as is.

## What changes

Replace the body of `ingest_course` with an enqueue. Accept an optional
`include_attachments` query param (default False, same gate default as
get_content) so a caller can ask for PDFs. Return **202 Accepted** with the job.

```python
from fastapi import Response, status
from app.routers.ingest_jobs import enqueue_ingest, ingest_job_status


@router.post("/{course_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_course(
    course_id: str = Depends(require_valid_course_id),
    include_attachments: bool = False,
    response: Response = None,
    user: CurrentUser = Depends(get_current_user),
):
    # No Blackboard call here any more. Enqueue and return immediately; the
    # worker's ingest_walk job drains the tree over its schedule, checkpointing
    # progress in ingest_jobs so a killed run resumes. See
    # docs/design/async-ingest.md for the full rationale (the old inline walk
    # measured 31.8s and timed out at the 30s wall).
    job = enqueue_ingest(
        institution_id=user.institution_id,
        course_id=course_id,
        include_attachments=include_attachments,
    )
    # 202 whether we created a job or found a live one; 200-with-existing would
    # be a lie (nothing new started) and an error would punish a harmless retry.
    return {
        "status": "queued" if job["created"] else "already_in_progress",
        "job": job,
        "message": "Ingest runs in the background; poll GET /{course_id}/ingest/status.",
    }
```

## Add a status route

So a caller (or the instructor dashboard) can watch progress instead of the old
"POST until the numbers stop moving" grind:

```python
@router.get("/{course_id}/ingest/status")
def ingest_status(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    job = ingest_job_status(course_id=course_id)
    if job is None:
        return {"status": "never_ingested", "job": None}
    return {"status": job["status"], "job": job}
```

## Dead code to remove (carefully)

Once the route enqueues, the inline store/embed phases in the old
`ingest_course` (the `existing_refs` fetch, the `for item in content_items`
store loop, the `_embed_pending` call, the `pendingTagging` count) are no longer
reached from this route. **Do not delete them blindly** — `_embed_pending` and
the dedupe query pattern are reused conceptually by the worker. Confirm nothing
else imports them, then remove only what is genuinely orphaned, in its own
commit separate from the behavior change, so the diff is reviewable.

## Tests

Mirror `test_course_sync_cache.py`'s style:
- enqueue creates a pending job and returns 202;
- a second enqueue while one is live is a no-op returning the same job id;
- status route returns never_ingested, then pending, then complete as the job
  row advances (drive the row directly in the test, no live Blackboard).
