"""Tag backfill: tag any content_items chunk that has been stored + embedded
but not yet run through the tagger.

WHY THIS IS A WORKER JOB, NOT AN API ENDPOINT. Tagging is one LLM call per
chunk against a reasoning model whose latency measured 3-150s per call, with
a single call able to exceed 30s on its own. It lived in the /ingest HTTP
endpoint (services/api), on the api Lambda's 30s wall — the wrong tool for a
minutes-long, unbounded batch. Every symptom (the 30s timeouts, the tight
time-slice, the manual re-POSTing until complete) came from running a
background job through a request-response door. This is the same shape as
embed_backfill: sweep for rows needing work, process a bounded batch, safe to
run repeatedly. The EventBridge schedule (rate(15 minutes)) drains a course's
backlog over the following runs with no human at a terminal.

The rows ARE the progress record — no job table, no cursor:
  - skill_id set                -> tagged, matched a skill (done)
  - tag_attempted_at set, no skill_id -> tagged, genuinely matched nothing (done,
    will not be retried unless /content/retag reopens it)
  - tag_attempted_at null       -> still pending

Failure semantics, carried over EXACTLY from the api's _tag_pending — this
distinction was hard-won over a whole debugging session, do not simplify it:
  - a TRANSPORT/HTTP failure (tagger raises) does NOT set tag_attempted_at,
    so the chunk is retried on a later run once the provider is healthy.
  - a real NO-MATCH (tagger returns skill_id=None) DOES set tag_attempted_at,
    so untaggable content stops being pending instead of looping forever.
  - empty text is marked attempted immediately (nothing will change on retry).

Per-chunk failure isolation, same as embed_backfill: one bad tag call must
not stop the batch.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db import supabase as db
from app.tagger import tag_content

logger = logging.getLogger("kala.worker")

# Generous per-run cap, same rationale as embed_backfill's _BATCH_LIMIT: a
# scheduled job does not need to clear a large backlog in one pass, and this
# bounds worst-case wall-clock so one run cannot run away. At ~1 slow tag call
# at a time against the worker's 120s ceiling, most runs will process far
# fewer than this; the next scheduled run continues. Deliberately count-bound,
# not time-bound — the worker's own 120s Lambda timeout is the real ceiling,
# and a mid-chunk kill just leaves that chunk unmarked (retried next run).
_BATCH_LIMIT = 40


def run(*, institution_id: str | None = None) -> dict:
    """Tag pending chunks for one institution, or all if institution_id is
    None. Groups pending chunks by course so each course is tagged against
    ITS OWN approved skills (tagging against another course's skills would be
    a correctness bug, not just noise)."""
    pending_filter = {
        "tag_attempted_at": "is.null",
        "chunk_text": "not.is.null",
        "select": "id,course_id,institution_id,chunk_text,module_ref",
        "limit": str(_BATCH_LIMIT),
    }
    if institution_id:
        pending_filter["institution_id"] = f"eq.{institution_id}"
    pending = db.select("content_items", pending_filter)

    if not pending:
        return {"attempted": 0, "tagged": 0, "no_match": 0, "failed": 0, "skipped_no_skills": 0}

    # Approved skills are per (institution, course). Cache them so a batch that
    # spans several courses does one skills query per course, not per chunk.
    skills_cache: dict[tuple[str, str], list[dict]] = {}

    def _skills_for(inst_id: str, course_id: str) -> list[dict]:
        key = (inst_id, course_id)
        if key not in skills_cache:
            skills_cache[key] = db.select("skills", {
                "institution_id": f"eq.{inst_id}",
                "course_id": f"eq.{course_id}",
                "status": "eq.approved",
                "select": "id,name",
            })
        return skills_cache[key]

    attempted = tagged = no_match = failed = skipped_no_skills = 0
    # First tagged chunk for a skill decides that skill's module_ref (only
    # fills a gap, never overrides a manual value) — same as the api path.
    skill_module_ref: dict[tuple[str, str], str] = {}

    for row in pending:
        inst_id = row["institution_id"]
        course_id = row["course_id"]
        skills = _skills_for(inst_id, course_id)
        if not skills:
            # No approved skills for this course yet: nothing to tag against.
            # Leave tag_attempted_at NULL so these chunks are retried once
            # skills get approved (that is exactly what /content/retag +
            # this job are for). Not counted as attempted.
            skipped_no_skills += 1
            continue

        attempted += 1
        text = row.get("chunk_text") or ""
        if not text.strip():
            # Nothing to tag and nothing will change on retry — mark attempted
            # so it leaves the pending set.
            _mark_attempted(row["id"])
            no_match += 1
            continue

        try:
            tag = tag_content(text=text, skills=skills)
        except Exception as exc:  # noqa: BLE001 — transient; leave unmarked to retry
            # Deliberately do NOT mark attempted: a provider/transport failure
            # is transient, and leaving the chunk pending is what makes a later
            # run retry it once the tagger is healthy again.
            logger.warning("tag_backfill: chunk %s failed (left for retry): %s", row["id"], exc)
            failed += 1
            continue

        skill_id = tag.get("skill_id")
        update = {"tag_attempted_at": datetime.now(timezone.utc).isoformat()}
        if skill_id:
            update["skill_id"] = skill_id
        db.update("content_items", {"id": f"eq.{row['id']}"}, update)

        if skill_id:
            tagged += 1
            module_ref = row.get("module_ref")
            key = (inst_id, skill_id)
            if module_ref and key not in skill_module_ref:
                skill_module_ref[key] = module_ref
        else:
            no_match += 1

    # Best-effort skill -> module inference, same as the api path: only fills a
    # null module_ref, never touches a manually-set one.
    for (inst_id, skill_id), module_ref in skill_module_ref.items():
        db.update(
            "skills",
            {"id": f"eq.{skill_id}", "institution_id": f"eq.{inst_id}", "module_ref": "is.null"},
            {"module_ref": module_ref},
        )

    return {
        "attempted": attempted,
        "tagged": tagged,
        "no_match": no_match,
        "failed": failed,
        "skipped_no_skills": skipped_no_skills,
    }


def _mark_attempted(row_id: str) -> None:
    db.update(
        "content_items",
        {"id": f"eq.{row_id}"},
        {"tag_attempted_at": datetime.now(timezone.utc).isoformat()},
    )
