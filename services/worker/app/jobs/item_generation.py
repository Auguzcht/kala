"""Drain the durable diagnostic/practice item-generation queue.

Rows in ``item_generation_jobs`` are the queue and progress record. This job
claims at most two eligible rows, runs synchronous structured-output calls in
a small thread pool, and checkpoints each row independently. It deliberately
does not use SQS or a second worker invocation: the queue table and the
15-minute schedule are the same pattern as ingest and tagging.

Budget contract:
  - 100 seconds for this job's model slice;
  - 90 seconds maximum per model HTTP call;
  - one validation reroll only when at least 85 seconds remain;
  - no provider/transport retry in the same invocation;
  - five scheduled attempts with 15/30/60/120/240 minute backoff.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from time import monotonic

from app.db import supabase as db
from app.item_gen import ItemGenerationError, NoCourseContentError, generate_question

logger = logging.getLogger("kala.worker")

_MAX_ROWS = 2
_JOB_BUDGET_SECONDS = 100.0
_CALL_TIMEOUT_SECONDS = 90.0
_MAX_ATTEMPTS = 5
_BACKOFF_MINUTES = (15, 30, 60, 120, 240)
_STALE_AFTER_SECONDS = 150


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _reclaim_stale(*, institution_id: str | None) -> int:
    cutoff = _now() - timedelta(seconds=_STALE_AFTER_SECONDS)
    filters = {
        "status": "eq.in_progress",
        "started_at": f"lt.{_iso(cutoff)}",
        "select": "id",
        "limit": "20",
    }
    if institution_id:
        filters["institution_id"] = f"eq.{institution_id}"
    rows = db.select("item_generation_jobs", filters)
    for row in rows:
        db.update(
            "item_generation_jobs",
            {"id": f"eq.{row['id']}", "status": "eq.in_progress"},
            {"status": "pending", "next_attempt_at": _iso(_now()), "updated_at": _iso(_now())},
        )
    return len(rows)


def _eligible_rows(*, institution_id: str | None) -> list[dict]:
    now = _iso(_now())
    filters = {
        "status": "eq.pending",
        "next_attempt_at": f"lte.{now}",
        "select": "id,institution_id,course_id,skill_id,kind,set_id,lesson_step_id,context_offset,attempt_count",
        "order": "next_attempt_at.asc",
        "limit": str(_MAX_ROWS),
    }
    if institution_id:
        filters["institution_id"] = f"eq.{institution_id}"
    return db.select("item_generation_jobs", filters)


def _claim(row: dict) -> dict | None:
    now = _iso(_now())
    claimed = db.update(
        "item_generation_jobs",
        {"id": f"eq.{row['id']}", "status": "eq.pending"},
        {"status": "in_progress", "started_at": now, "updated_at": now},
    )
    return claimed[0] if claimed else None


def _existing_item(row: dict) -> bool:
    """Find an item persisted before a worker kill checkpointed the queue.

    ``item_gen`` uses the queue id as the generated item id. This makes the
    persist-then-checkpoint gap recoverable without guessing which practice
    offset a same-set item belongs to.
    """
    item_kind = "tutor" if row["kind"] == "lesson" else row["kind"]
    found = db.select("generated_items", {
        "id": f"eq.{row['id']}",
        "institution_id": f"eq.{row['institution_id']}",
        "course_id": f"eq.{row['course_id']}",
        "skill_id": f"eq.{row['skill_id']}",
        "kind": f"eq.{item_kind}",
        "select": "id",
        "limit": "1",
    })
    return bool(found)


def _complete(row: dict) -> None:
    if row["kind"] == "lesson":
        # guided_lesson_steps has no institution_id of its own. Verify the
        # parent lesson through the same relationship used by its RLS policy
        # before writing the generated tutor item onto the step.
        steps = db.select("guided_lesson_steps", {
            "id": f"eq.{row['lesson_step_id']}",
            "guided_lessons.institution_id": f"eq.{row['institution_id']}",
            "select": "id,lesson_id,guided_lessons!inner(institution_id)",
            "limit": "1",
        })
        if not steps:
            raise ItemGenerationError("lesson step is not owned by queue institution")
        db.update(
            "guided_lesson_steps",
            {"id": f"eq.{steps[0]['id']}", "lesson_id": f"eq.{steps[0]['lesson_id']}"},
            {"check_item_id": row["id"]},
        )
    now = _iso(_now())
    db.update(
        "item_generation_jobs",
        {"id": f"eq.{row['id']}", "status": "eq.in_progress"},
        {
            "status": "complete", "item_id": row["id"],
            "finished_at": now, "updated_at": now, "last_error": None,
        },
    )


def _failure(row: dict, exc: Exception) -> str:
    attempt = int(row.get("attempt_count") or 0) + 1
    now = _now()
    values = {
        "attempt_count": attempt,
        "last_error": type(exc).__name__,
        "updated_at": _iso(now),
    }
    if attempt >= _MAX_ATTEMPTS:
        values.update({"status": "failed", "finished_at": _iso(now)})
        outcome = "failed"
    else:
        retry_at = now + timedelta(minutes=_BACKOFF_MINUTES[attempt - 1])
        values.update({"status": "pending", "next_attempt_at": _iso(retry_at)})
        outcome = "retrying"
    db.update(
        "item_generation_jobs",
        {"id": f"eq.{row['id']}", "status": "eq.in_progress"},
        values,
    )
    logger.warning(
        "item_generation: row %s %s after attempt %d (%s)",
        row["id"], outcome, attempt, type(exc).__name__,
    )
    return outcome


def _process(row: dict, *, deadline: float) -> str:
    try:
        if _existing_item(row):
            _complete(row)
            return "reconciled"

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("item generation budget exhausted before model call")

        skills = db.select("skills", {
            "id": f"eq.{row['skill_id']}",
            "institution_id": f"eq.{row['institution_id']}",
            "course_id": f"eq.{row['course_id']}",
            "status": "eq.approved",
            "select": "id,name,bloom_level",
            "limit": "1",
        })
        if not skills:
            raise ItemGenerationError("approved skill not found for queued item")

        item_kind = "tutor" if row["kind"] == "lesson" else row["kind"]
        generate_question(
            institution_id=row["institution_id"],
            course_id=row["course_id"],
            skill=skills[0],
            kind=item_kind,
            job_id=row["id"],
            set_id=row.get("set_id"),
            context_offset=int(row.get("context_offset") or 0),
            deadline=deadline,
            call_timeout_seconds=min(_CALL_TIMEOUT_SECONDS, remaining),
        )
        _complete(row)
        return "completed"
    except NoCourseContentError as exc:
        return _failure(row, exc)
    except Exception as exc:  # noqa: BLE001 — isolate each queue row's failure
        return _failure(row, exc)


def run(*, institution_id: str | None = None, remaining_seconds: float | None = None) -> dict:
    started = monotonic()
    budget = _JOB_BUDGET_SECONDS if remaining_seconds is None else min(
        _JOB_BUDGET_SECONDS, max(0.0, remaining_seconds),
    )
    deadline = started + budget
    reclaimed = _reclaim_stale(institution_id=institution_id)
    candidates = _eligible_rows(institution_id=institution_id)[:_MAX_ROWS]

    claimed: list[dict] = []
    for row in candidates:
        if deadline - monotonic() <= 5:
            break
        current = _claim(row)
        if current:
            claimed.append(current)

    if not claimed:
        return {
            "reclaimed": reclaimed, "claimed": 0, "completed": 0,
            "reconciled": 0, "retrying": 0, "failed": 0,
            "budget_exhausted": False,
        }

    outcomes: list[str] = []
    with ThreadPoolExecutor(max_workers=_MAX_ROWS) as executor:
        futures = [executor.submit(_process, row, deadline=deadline) for row in claimed]
        for future in as_completed(futures):
            outcomes.append(future.result())

    return {
        "reclaimed": reclaimed,
        "claimed": len(claimed),
        "completed": outcomes.count("completed"),
        "reconciled": outcomes.count("reconciled"),
        "retrying": outcomes.count("retrying"),
        "failed": outcomes.count("failed"),
        "budget_exhausted": monotonic() >= deadline,
    }
