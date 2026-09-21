"""Enqueue side of async ingest, for the api.

The api no longer walks the course tree in the request (that moved to the
worker's ingest_walk job — see services/worker/app/jobs/ingest_walk.py and
docs/design/async-ingest.md). POST /ingest now enqueues a job and returns 202.

This module is the thin enqueue helper the /ingest route calls. Kept separate
so the route change in diagnostic.py is a few lines and the enqueue logic
(including the "one live job per course" no-op) is testable on its own.

STATUS: SCAFFOLD. Logic is complete and mirrors the codebase's db access
style. DeepSeek: wire it into diagnostic.py's /ingest route (see
diagnostic.py.INGEST_ROUTE.PATCH.md) and add tests alongside
test_course_sync_cache.py.
"""
from __future__ import annotations

import logging

import httpx

from app.db import supabase as db

logger = logging.getLogger(__name__)

_LIVE_JOB_FILTER_SELECT = (
    "id,status,include_attachments,folders_expanded,items_stored,pdfs_fetched"
)


def enqueue_ingest(
    *, institution_id: str, course_id: str, include_attachments: bool = False,
) -> dict:
    """Enqueue a course ingest job, or return the existing live one.

    Idempotent by design: the ingest_jobs table has a partial unique index
    (one live job per course), so a double-click or retry cannot spawn a second
    walk against Blackboard's quota. If a live job already exists we return it
    unchanged rather than erroring — the caller sees the same 202 either way.

    Returns the job row (new or existing) plus `created: bool` so the route can
    say which happened. Never walks the tree, never calls Blackboard — this is
    O(1) and safe on the api's 30s wall by a wide margin.
    """
    existing = _live_job(course_id)
    if existing:
        logger.info(
            "ingest enqueue no-op: live job=%s status=%s already exists for course=%s",
            existing["id"], existing["status"], course_id,
        )
        return {**existing, "created": False}

    # Fixed: two concurrent callers can both pass the SELECT above (both see
    # "no live job") and both proceed to INSERT. The partial unique index
    # (one live job per course) correctly lets only one INSERT through — but
    # the loser previously had nothing catching the resulting conflict, so
    # db.insert's raise_for_status() propagated a bare HTTPStatusError and the
    # caller saw a 500, not the 202 the docstring promises. That was half the
    # idempotency contract: the read-then-write race window between the
    # SELECT above and this INSERT is real under concurrent requests (two
    # Lambda invocations handling a double-click), not just theoretical.
    try:
        rows = db.insert("ingest_jobs", [{
            "institution_id": institution_id,
            "course_id": course_id,
            "status": "pending",
            "include_attachments": include_attachments,
        }])
    except httpx.HTTPStatusError as exc:
        response = exc.response
        if response is not None and response.status_code == 409:
            # PostgREST maps the unique-index violation (Postgres 23505) to a
            # 409. We lost the race: another caller's row landed first between
            # our SELECT and our INSERT. Re-select and return THAT row, same
            # shape as the existing-live-job branch above, so a double-click
            # or retry gets a 202 with the winning job either way, never a 500.
            winner = _live_job(course_id)
            if winner:
                logger.info(
                    "ingest enqueue lost race for course=%s; returning live job=%s",
                    course_id, winner["id"],
                )
                return {**winner, "created": False}
            # Got a 409 but no live job is visible (e.g. it completed/failed
            # in the instant between the conflict and our re-select — narrow,
            # but possible). Surface the original error rather than guessing.
            logger.error(
                "ingest enqueue got 409 for course=%s but no live job found on "
                "re-select",
                course_id,
            )
        raise

    if not rows:
        raise RuntimeError("failed to enqueue ingest job")
    job = rows[0]
    logger.info(
        "ingest enqueued job=%s course=%s include_attachments=%s",
        job["id"], course_id, include_attachments,
    )
    return {**job, "created": True}


def _live_job(course_id: str) -> dict | None:
    """The current pending/in_progress job for a course, if any. Shared by the
    happy-path check and the race-recovery path so both look at the exact same
    filter and field set."""
    rows = db.select("ingest_jobs", {
        "course_id": f"eq.{course_id}",
        "status": "in.(pending,in_progress)",
        "select": _LIVE_JOB_FILTER_SELECT,
        "limit": "1",
    })
    return rows[0] if rows else None


def ingest_job_status(*, course_id: str) -> dict | None:
    """Latest ingest job for a course, for a GET status route or the instructor
    dashboard. Newest first; None if the course has never been ingested."""
    rows = db.select("ingest_jobs", {
        "course_id": f"eq.{course_id}",
        "select": "id,status,frontier,folders_expanded,items_stored,pdfs_fetched,"
                  "last_error,created_at,started_at,updated_at,finished_at",
        "order": "created_at.desc",
        "limit": "1",
    })
    return rows[0] if rows else None
