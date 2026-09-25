"""API-side enqueue and read helpers for async item generation.

The queue table is operational state, not a client-facing resource. These
helpers keep every lookup tenant-scoped and turn the partial unique indexes
into idempotent route behavior: a concurrent diagnostic request that loses the
insert race returns the winning row instead of a 500.
"""
from __future__ import annotations

import logging

import httpx

from app.db import supabase as db

logger = logging.getLogger(__name__)

_QUEUE_SELECT = (
    "id,institution_id,course_id,skill_id,kind,set_id,context_offset,status,"
    "attempt_count,item_id,last_error,next_attempt_at,created_at,finished_at"
)


def diagnostic_job(*, institution_id: str, course_id: str, skill_id: str) -> dict | None:
    rows = db.select("item_generation_jobs", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "skill_id": f"eq.{skill_id}",
        "kind": "eq.diagnostic",
        "select": _QUEUE_SELECT,
        "order": "created_at.desc",
        "limit": "1",
    })
    return rows[0] if rows else None


def enqueue_diagnostic(
    *, institution_id: str, course_id: str, skill_id: str,
) -> tuple[dict, bool]:
    """Return the live/history row, inserting the diagnostic request if absent.

    A terminal failed row is returned as-is. GET /diagnostic deliberately does
    not reopen it; reopening is an explicit follow-up operation outside this
    pass. The unique live index closes the SELECT/INSERT race window.
    """
    existing = diagnostic_job(
        institution_id=institution_id, course_id=course_id, skill_id=skill_id,
    )
    if existing:
        return existing, False

    try:
        rows = db.insert("item_generation_jobs", [{
            "institution_id": institution_id,
            "course_id": course_id,
            "skill_id": skill_id,
            "kind": "diagnostic",
            "context_offset": 0,
        }])
    except httpx.HTTPStatusError as exc:
        response = exc.response
        if response is not None and response.status_code == 409:
            winner = diagnostic_job(
                institution_id=institution_id,
                course_id=course_id,
                skill_id=skill_id,
            )
            if winner:
                logger.info(
                    "diagnostic enqueue lost race course=%s skill=%s job=%s",
                    course_id, skill_id, winner["id"],
                )
                return winner, False
        raise

    if not rows:
        raise RuntimeError("failed to enqueue diagnostic item")
    return rows[0], True


def practice_jobs(*, institution_id: str, course_id: str, set_id: str) -> list[dict]:
    return db.select("item_generation_jobs", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "set_id": f"eq.{set_id}",
        "kind": "eq.practice",
        "select": _QUEUE_SELECT,
        "order": "context_offset.asc",
    })


def enqueue_practice(
    *, institution_id: str, course_id: str, skill_id: str, set_id: str, size: int,
) -> list[dict]:
    try:
        rows = db.insert("item_generation_jobs", [{
            "institution_id": institution_id,
            "course_id": course_id,
            "skill_id": skill_id,
            "kind": "practice",
            "set_id": set_id,
            "context_offset": offset,
        } for offset in range(size)])
    except httpx.HTTPStatusError as exc:
        response = exc.response
        if response is not None and response.status_code == 409:
            logger.warning(
                "practice enqueue got 409; rereading existing offsets "
                "course=%s set=%s",
                course_id, set_id,
            )
            recovered = practice_jobs(
                institution_id=institution_id, course_id=course_id, set_id=set_id,
            )
            if len(recovered) < size:
                logger.error(
                    "practice enqueue recovered only %d/%d offsets after 409 "
                    "course=%s set=%s",
                    len(recovered), size, course_id, set_id,
                )
            return recovered
        raise
    if len(rows) == size:
        return rows

    # A partial response is unexpected for a new set, but reread once so a
    # PostgREST response interrupted after commit remains recoverable.
    logger.warning(
        "practice enqueue returned %d/%d rows; rereading offsets "
        "course=%s set=%s",
        len(rows), size, course_id, set_id,
    )
    recovered = practice_jobs(
        institution_id=institution_id, course_id=course_id, set_id=set_id,
    )
    if len(recovered) < size:
        logger.error(
            "practice enqueue recovered only %d/%d offsets after partial insert "
            "course=%s set=%s",
            len(recovered), size, course_id, set_id,
        )
    return recovered
