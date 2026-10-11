"""Practice endpoints. Mirrors the diagnostic path: pick the weakest skill
for this student, generate a fresh RAG-grounded item against real course
content, grade it server-side, write evidence, and roll the result into the
mastery tracer.

Two ways to get practice content:
  - GET  /next  — a single item, generated on request. Retained as the
    weakest-skill single-item path (nothing outside PracticePanel calls it)
    so this migration adds a batch path without removing a working one.
  - POST /set   — a batch of N items for one skill, generated concurrently
    and grouped under a quiz_sets row. This is the session path: the client
    holds the set and advances locally, so answering five questions costs one
    model round trip's worth of wall-clock time instead of five serial ones.
    Grading is identical either way — a set is delivery grouping, not a new
    grading unit (see 0012_quiz_sets.sql).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter_ns
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError
from pydantic import BaseModel

from app.bank.kick import kick_bank
from app.bank.serving import MIN_USABLE, bank_enabled, pick_bank_items_with_meta, record_exposure
from app.db import supabase as db
from app.deps import (
    CurrentUser,
    get_current_user,
    require_valid_course_id,
    require_valid_set_id,
)
from app.learn import items as item_gen
from app.routers.item_generation_jobs import enqueue_practice, practice_jobs

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/practice", tags=["practice"])

# One sitting's worth of practice questions. Bounded so a set is a set, not an
# unbounded generation fan-out: N items means N concurrent model calls (see
# ai/concurrency.py), and this keeps that fan-out inside one request's budget.
MAX_SET_SIZE = 10
DEFAULT_SET_SIZE = 5
BANK_SET_SIZES = {5, 10, 20}


def _resolve_skill(*, institution_id: str, user_id: str, course_id: str,
                   skill_id: str | None) -> dict | None:
    """Resolve the one skill a session runs against: an explicit picker
    choice (validated — it is client input), or the student's weakest skill.
    Returns None when the course has no approved skills, which callers turn
    into an empty result rather than generating against nothing.

    Shared by /next and /set so the two paths can never drift on what counts
    as a valid skill or what 'weakest' means.
    """
    if skill_id:
        # Explicit topic choice from the picker — validate it's a real,
        # approved skill in THIS course before generating against it. The
        # weakest-skill path below never needs this check because it's
        # derived server-side from the course's own approved skills; this
        # path takes a client-supplied id and must not trust it blindly.
        rows = db.select("skills", {
            "id": f"eq.{skill_id}", "course_id": f"eq.{course_id}",
            "institution_id": f"eq.{institution_id}", "status": "eq.approved",
            "select": "id,name,bloom_level", "limit": "1",
        })
        skill = rows[0] if rows else None
        if not skill:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found")
        return skill
    return item_gen.weakest_skill(
        institution_id=institution_id, user_id=user_id, course_id=course_id,
    )


def _item_view(row: dict) -> dict:
    """Return the client-safe portion of a generated item."""
    return {
        "id": row["id"], "skillId": row["skill_id"],
        "bloomLevel": row.get("bloom_level"),
        "prompt": row["prompt"], "choices": row.get("choices") or [],
    }


def _bank_course(*, institution_id: str, course_id: str) -> dict | None:
    try:
        rows = db.select("courses", {
            "id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
            "select": "id,bank_serving", "limit": "1",
        })
    except Exception:  # noqa: BLE001 - preserve the legacy fallback if old schemas are in use
        return None
    return rows[0] if rows else None


def _bank_state(*, course_id: str, skill_id: str) -> dict | None:
    rows = db.select("skill_bank_state", {
        "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}",
        "select": "skill_id,status,mcq_ready,mcq_target,depth", "limit": "1",
    })
    return rows[0] if rows else None


def _bank_status(state: dict | None) -> dict:
    state = state or {}
    ready = int(state.get("mcq_ready") or 0)
    return {
        "status": state.get("status") or "waiting_content",
        "mcqReady": ready,
        "mcqTarget": int(state.get("mcq_target") or 0),
        "usable": ready >= MIN_USABLE,
    }


def _bank_set_response(*, course_id: str, skill_id: str, requested_size: int,
                       status_value: str, bank_status: dict, items: list[dict] | None = None,
                       set_id: str | None = None, includes_repeats: bool = False) -> dict:
    items = items or []
    return {
        "courseId": course_id, "setId": set_id, "skillId": skill_id,
        "kind": "practice", "status": status_value,
        "requestedSize": requested_size, "readyCount": len(items),
        "pendingCount": 0, "failedCount": 0, "failedOffsets": [],
        "items": [_item_view(item) for item in items],
        "bankStatus": bank_status, "includesRepeats": includes_repeats,
    }


def _practice_set_view(
    *, course_id: str, set_row: dict, jobs: list[dict], items: list[dict],
    unavailable: bool = False,
) -> dict:
    requested_size = int(set_row.get("size") or 0)
    pending_count = sum(job["status"] in {"pending", "in_progress"} for job in jobs)
    failed_jobs = [job for job in jobs if job["status"] == "failed"]
    complete_count = sum(job["status"] == "complete" for job in jobs)
    failed_count = len(failed_jobs)
    # Complete queue rows are the only rows allowed to contribute playable
    # items. The generated_items query is tenant-scoped and answer-sanitized.
    ready_count = len(items)
    resolved_count = complete_count + failed_count
    # No queue rows means this is a legacy synchronous/from-items set created
    # before 0019, not a current async set that silently lost its queue.
    # Current create_set rejects that latter condition before returning.
    status_value = "unavailable" if unavailable else (
        ("ready" if ready_count else "failed") if not jobs else
        ("generating" if pending_count or resolved_count < requested_size
         else ("ready" if ready_count else "failed"))
    )
    return {
        "courseId": course_id,
        "setId": set_row["id"],
        "skillId": set_row["skill_id"],
        "kind": set_row["kind"],
        "status": status_value,
        "available": not unavailable,
        "requestedSize": requested_size,
        "readyCount": ready_count,
        "pendingCount": pending_count,
        "failedCount": failed_count,
        "failedOffsets": [job["context_offset"] for job in failed_jobs],
        "items": [_item_view(item) for item in items],
    }


@router.get("/{course_id}/next")
def next_item(
    course_id: str = Depends(require_valid_course_id),
    skill_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    skill = _resolve_skill(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id,
    )
    if not skill:
        return {"courseId": course_id, "item": None}
    course = _bank_course(institution_id=user.institution_id, course_id=course_id)
    if course and bank_enabled(course, "test"):
        state = _bank_state(course_id=course_id, skill_id=skill["id"])
        bank_status = _bank_status(state)
        if not bank_status["usable"]:
            return {"courseId": course_id, "item": None, "bankStatus": bank_status}
        items, _ = pick_bank_items_with_meta(
            user.user_id, course_id, skill["id"], 1, "test",
            institution_id=user.institution_id,
        )
        if not items:
            return {"courseId": course_id, "item": None, "bankStatus": bank_status}
        item = items[0]
        record_exposure(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=item["skill_id"], item_id=item["id"], tested=True,
        )
        return {"courseId": course_id, "item": _item_view(item), "bankStatus": bank_status}
    item = item_gen.generate_question(
        institution_id=user.institution_id, course_id=course_id,
        skill=skill, kind="practice",
    )
    return {"courseId": course_id, "item": item}


@router.post("/{course_id}/set", status_code=status.HTTP_202_ACCEPTED)
def create_set(
    course_id: str = Depends(require_valid_course_id),
    skill_id: str | None = None,
    size: int = DEFAULT_SET_SIZE,
    user: CurrentUser = Depends(get_current_user),
):
    """Queue a batch of practice items for ONE skill under a quiz_sets row.
    This is the async batch replacement for calling /next N times.

    The set row is created FIRST, then one durable queue row per context offset
    is inserted. The worker writes each generated item with this set_id and
    checkpoints its queue row. The route returns before any model call.

    A POST, not a GET: this has a side effect (persists N queue rows), so it
    must not be cached or prefetched like the read-shaped /next is.
    """
    if size < 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "size must be at least 1")

    skill = _resolve_skill(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id,
    )
    # Same guard /next has: no approved skill means nothing to generate
    # against, so return an empty set rather than fanning out over nothing
    # (map_concurrent short-circuits on empty input, but an empty set row with
    # no skill to attribute it to is meaningless — better to return null).
    if not skill:
        return {
            "courseId": course_id, "setId": None, "status": "failed",
            "requestedSize": size, "readyCount": 0, "pendingCount": 0,
            "failedCount": 0, "failedOffsets": [], "items": [],
        }

    course = _bank_course(institution_id=user.institution_id, course_id=course_id)
    if course and bank_enabled(course, "test"):
        if size not in BANK_SET_SIZES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "bank set size must be 5, 10, or 20")
        state = _bank_state(course_id=course_id, skill_id=skill["id"])
        bank_status = _bank_status(state)
        if bank_status["status"] == "no_material":
            return JSONResponse(_bank_set_response(
                course_id=course_id, skill_id=skill["id"], requested_size=size,
                status_value="no_material", bank_status=bank_status,
            ), status_code=status.HTTP_200_OK)
        if not bank_status["usable"]:
            kick_bank(course_id, "test")
            return JSONResponse(_bank_set_response(
                course_id=course_id, skill_id=skill["id"], requested_size=size,
                status_value="preparing", bank_status=bank_status,
            ), status_code=status.HTTP_200_OK)
        items, includes_repeats = pick_bank_items_with_meta(
            user.user_id, course_id, skill["id"], size, "test",
            institution_id=user.institution_id,
        )
        if not items:
            return JSONResponse(_bank_set_response(
                course_id=course_id, skill_id=skill["id"], requested_size=size,
                status_value="preparing", bank_status=bank_status,
            ), status_code=status.HTTP_200_OK)
        set_rows = db.insert("quiz_sets", [{
            "institution_id": user.institution_id, "course_id": course_id,
            "skill_id": skill["id"], "kind": "practice", "size": len(items),
        }])
        set_id = set_rows[0]["id"]
        db.insert("quiz_set_items", [
            {"set_id": set_id, "item_id": item["id"], "position": position}
            for position, item in enumerate(items)
        ], prefer="return=minimal")
        for item in items:
            record_exposure(
                institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
                skill_id=item["skill_id"], item_id=item["id"], tested=True,
            )
        return JSONResponse(_bank_set_response(
            course_id=course_id, skill_id=skill["id"], requested_size=size,
            status_value="ready", bank_status=bank_status, items=items,
            set_id=set_id, includes_repeats=includes_repeats,
        ), status_code=status.HTTP_200_OK)

    size = min(size, MAX_SET_SIZE)

    set_rows = db.insert("quiz_sets", [{
        "institution_id": user.institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "kind": "practice",
        "size": size,
    }])
    set_id = set_rows[0]["id"]
    jobs = enqueue_practice(
        institution_id=user.institution_id, course_id=course_id,
        skill_id=skill["id"], set_id=set_id, size=size,
    )
    if len(jobs) < size:
        logger.error(
            "new practice set has only %d/%d queue rows; refusing dead set "
            "course=%s set=%s",
            len(jobs), size, course_id, set_id,
        )
        db.delete("quiz_sets", {"id": f"eq.{set_id}"})
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "practice set could not be queued; please try again",
        )
    # A newly-created set is pending by construction. Keep the response
    # derived from the queue rows so a unique-index recovery or a future
    # idempotent enqueue path cannot claim a different state than the worker.
    return _practice_set_view(
        course_id=course_id, set_row=set_rows[0], jobs=jobs, items=[],
    )


class FromItemsBody(BaseModel):
    item_ids: list[str]


@router.post("/{course_id}/set/from-items")
def create_set_from_items(
    body: FromItemsBody,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Group ALREADY-GENERATED items into a quiz set — the study -> test
    bridge. "Test me on these" from the study deck hands the exact items the
    student just studied here, so the quiz tests recognition of what they saw;
    Optionally later, a fresh-items variant can call /set instead. This is
    additive: it does NOT generate and does NOT grade — it is a caller of the
    same quiz machinery, wrapping existing rows in a quiz_sets grouping.

    Tenant safety: every item id is client-supplied, so each is verified to
    belong to this institution AND course before it is grouped. Ids from
    another course/institution are dropped (and the request 404s if none
    survive) rather than silently attaching foreign items to a set in this
    course.

    Items must share one skill — a set is per-skill (quiz_sets.skill_id is NOT
    NULL). A cross-skill deck ("review what's due") therefore can't bridge as
    one set; the client sends one skill's items at a time, which is the
    honest shape for "test me on this topic."
    """
    item_ids = list(dict.fromkeys(body.item_ids))  # de-dupe, keep order
    if not item_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "item_ids must not be empty")

    rows = db.select("generated_items", {
        "id": f"in.({','.join(item_ids)})",
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}",
        "retired_at": "is.null", "skills.status": "eq.approved",
        "select": "id,skill_id,prompt,choices,bloom_level,skills!inner(status)",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such items in this course")

    skill_ids = {r["skill_id"] for r in rows if r.get("skill_id")}
    if len(skill_ids) != 1:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "a set is scoped to one skill; items must share a skill",
        )
    skill_id = skill_ids.pop()

    # Preserve the caller's order, dropping anything that didn't survive the
    # tenant check, so the quiz runs in the order the student studied.
    found = {r["id"]: r for r in rows}
    ordered = [found[i] for i in item_ids if i in found]

    set_rows = db.insert("quiz_sets", [{
        "institution_id": user.institution_id,
        "course_id": course_id,
        "skill_id": skill_id,
        "kind": "practice",
        "size": len(ordered),
    }])
    set_id = set_rows[0]["id"]

    db.insert("quiz_set_items", [
        {"set_id": set_id, "item_id": item["id"], "position": position}
        for position, item in enumerate(ordered)
    ], prefer="return=minimal")
    for item in ordered:
        record_exposure(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=item["skill_id"], item_id=item["id"], tested=True,
        )

    return {
        "courseId": course_id,
        "setId": set_id,
        "items": [{
            "id": r["id"], "skillId": r["skill_id"],
            "bloomLevel": r.get("bloom_level"),
            "prompt": r["prompt"], "choices": r.get("choices") or [],
        } for r in ordered],
    }


class SubmitBody(BaseModel):
    item_id: str
    choice_id: str
    latency_ms: int = 0
    set_id: str | None = None
    session_id: UUID | None = None
    idempotency_key: str | None = None


def _mastery_display(value: float | None, level: str | None = None) -> dict:
    """Keep the response band's label aligned with the student twin."""
    if level is None:
        level = (
            "No evidence" if value is None else
            "Developing" if value < 0.4 else
            "Proficient" if value < 0.7 else
            "Mastered"
        )
    return {"level": level, "value": value}


def _attempts_by_set(*, institution_id: str, user_id: str, set_ids: list[str]) -> dict[str, dict]:
    """This student's attempt row per set, keyed by set_id. One query for a
    whole list rather than N — the Test tab renders many sets at once.

    quiz_sets itself is shared course content (no user_id); the personal half
    lives in quiz_set_attempts, written only by submit(). A set with no row
    simply means "never attempted by this student" and is absent from the
    map, which callers translate to null.
    """
    if not set_ids:
        return {}
    rows = db.select("quiz_set_attempts", {
        "institution_id": f"eq.{institution_id}",
        "user_id": f"eq.{user_id}",
        "set_id": f"in.({','.join(set_ids)})",
        "select": "set_id,attempted_count,correct_count,last_attempted_at",
    })
    return {r["set_id"]: r for r in rows}


def _attempt_view(row: dict | None) -> dict:
    """The set-level attempt metadata the UI badge reads. Null fields (not a
    missing key) for a set the student has never attempted, so the client can
    branch on `attemptedCount == null` without a separate existence flag."""
    if not row:
        return {"attemptedCount": None, "correctCount": None, "lastAttemptedAt": None}
    return {
        "attemptedCount": row["attempted_count"],
        "correctCount": row["correct_count"],
        "lastAttemptedAt": row.get("last_attempted_at"),
    }


def _item_counts_by_set(*, institution_id: str, set_ids: list[str]) -> dict[str, int]:
    """How many items each set actually holds, keyed by set_id. One query for
    a whole page of sets, so the list does not make the detail's count a lie.
    """
    if not set_ids:
        return {}
    links = db.select("quiz_set_items", {
        "set_id": f"in.({','.join(set_ids)})",
        "select": "set_id,item_id",
    })
    if not links or any("item_id" not in r for r in links):
        active_rows = db.select("generated_items", {
            "set_id": f"in.({','.join(set_ids)})", "institution_id": f"eq.{institution_id}",
            "retired_at": "is.null", "skills.status": "eq.approved",
            "select": "set_id,skills!inner(status)",
        })
        return _count_set_rows(active_rows)
    item_ids = list(dict.fromkeys(r["item_id"] for r in links))
    active = db.select("generated_items", {
        "id": f"in.({','.join(item_ids)})", "institution_id": f"eq.{institution_id}",
        "retired_at": "is.null", "skills.status": "eq.approved",
        "select": "id,skills!inner(status)",
    }) if item_ids else []
    active_ids = {r["id"] for r in active}
    return _count_set_rows(r for r in links if r["item_id"] in active_ids)


def _count_set_rows(rows) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["set_id"]] = counts.get(r["set_id"], 0) + 1
    return counts


@router.get("/{course_id}/sets")
def list_sets(
    course_id: str = Depends(require_valid_course_id),
    skill_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Saved quiz sets for this course, newest first, optionally scoped to one
    skill. Read-only: this is the Test tab's set browser. Each set carries
    THIS student's attempt metadata (or nulls for never-attempted) so the
    badge renders from one round trip.
    """
    params = {
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}",
        "select": "id,skill_id,kind,size,created_at",
        "order": "created_at.desc",
    }
    if skill_id:
        params["skill_id"] = f"eq.{skill_id}"
    rows = db.select("quiz_sets", params)
    attempts = _attempts_by_set(
        institution_id=user.institution_id, user_id=user.user_id,
        set_ids=[r["id"] for r in rows],
    )
    # Derive the count from the items that ACTUALLY exist rather than trusting
    # quiz_sets.size. That column is written at creation and corrected after a
    # partial batch, but a correction can be missed (a Lambda timing out
    # mid-request, a crash between generation and the follow-up update), and
    # when it is the list claims one number while the detail shows another —
    # "5 questions" opening onto 3. The item count is the truth; the column is
    # a cache of it. One grouped query for the whole page.
    counts = _item_counts_by_set(
        institution_id=user.institution_id, set_ids=[r["id"] for r in rows],
    )
    return {
        "courseId": course_id,
        "sets": [{
            "setId": r["id"], "skillId": r["skill_id"], "kind": r["kind"],
            "size": counts.get(r["id"], 0), "createdAt": r["created_at"],
            "status": "available" if counts.get(r["id"], 0) else "unavailable",
            **_attempt_view(attempts.get(r["id"])),
        } for r in rows],
    }


@router.get("/{course_id}/sets/{set_id}")
def get_set(
    course_id: str = Depends(require_valid_course_id),
    set_id: str = Depends(require_valid_set_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Load one saved set's items so it can be retaken or re-entered — the
    read behind the study->test bridge navigation and the retake list. Items
    are returned in their natural order (oldest first, the order they were
    generated/studied in via the set_id grouping).

    Ownership is verified against institution + course before anything is
    returned; a set id from another course 404s rather than leaking items.

    Item select is deliberately unchanged: prompts and choices only, never the
    answer key (correct_choice_id/explanation). This is a graded test, not a
    flashcard browse — the client must not be able to see the answers before
    submitting. Only SET-LEVEL metadata gains the attempt fields.
    """
    sets = db.select("quiz_sets", {
        "id": f"eq.{set_id}",
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}",
        "select": "id,skill_id,kind,size,created_at", "limit": "1",
    })
    if not sets:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "set not found")

    links = db.select("quiz_set_items", {
        "set_id": f"eq.{set_id}", "select": "item_id,position", "order": "position.asc",
    })
    if not links or any("item_id" not in row for row in links):
        legacy = db.select("generated_items", {
            "set_id": f"eq.{set_id}", "institution_id": f"eq.{user.institution_id}",
            "retired_at": "is.null", "skills.status": "eq.approved",
            "select": "id,created_at,skills!inner(status)", "order": "created_at.asc",
        })
        links = [{"item_id": row["id"], "position": index} for index, row in enumerate(legacy)]
    item_ids = [r["item_id"] for r in links]
    items = db.select("generated_items", {
        "id": f"in.({','.join(item_ids)})" if item_ids else "in.(00000000-0000-0000-0000-000000000000)",
        "institution_id": f"eq.{user.institution_id}",
        "retired_at": "is.null", "skills.status": "eq.approved",
        "select": "id,skill_id,prompt,choices,bloom_level,skills!inner(status)",
    })
    items_by_id = {r["id"]: r for r in items}
    items = [items_by_id[r["item_id"]] for r in links if r["item_id"] in items_by_id]
    for item in items:
        record_exposure(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=item["skill_id"], item_id=item["id"], tested=True,
        )
    jobs = practice_jobs(
        institution_id=user.institution_id, course_id=course_id, set_id=set_id,
    )
    s = sets[0]
    unavailable = bool(links) and not items
    attempts = _attempts_by_set(
        institution_id=user.institution_id, user_id=user.user_id, set_ids=[s["id"]],
    )
    return {
        **_practice_set_view(course_id=course_id, set_row=s, jobs=jobs, items=items,
                             unavailable=unavailable),
        **_attempt_view(attempts.get(s["id"])),
    }


@router.get("/{course_id}/sets/{set_id}/results")
def get_set_results(
    course_id: str = Depends(require_valid_course_id),
    set_id: str = Depends(require_valid_set_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Return the durable recap for this student's answers in one set.

    Only practice_answer_results rows expose answer keys. Unanswered set items
    are assembled from prompt/choices columns alone.
    """
    sets = db.select("quiz_sets", {
        "id": f"eq.{set_id}", "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}", "select": "id,skill_id", "limit": "1",
    })
    if not sets:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "set not found")

    links = db.select("quiz_set_items", {
        "set_id": f"eq.{set_id}", "select": "item_id,position", "order": "position.asc",
    })
    if not links:
        legacy = db.select("generated_items", {
            "set_id": f"eq.{set_id}", "institution_id": f"eq.{user.institution_id}",
            "select": "id,created_at", "order": "created_at.asc",
        })
        links = [{"item_id": row["id"], "position": index} for index, row in enumerate(legacy)]
    item_ids = [row["item_id"] for row in links if row.get("item_id")]
    item_rows = db.select("generated_items", {
        "id": f"in.({','.join(item_ids)})" if item_ids else "in.(00000000-0000-0000-0000-000000000000)",
        "institution_id": f"eq.{user.institution_id}",
        # Do not request correct_choice_id or explanation in this set-wide query.
        "select": "id,prompt,choices",
    })
    result_rows = db.select("practice_answer_results", {
        "institution_id": f"eq.{user.institution_id}", "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}", "set_id": f"eq.{set_id}",
        "select": "*", "order": "created_at.asc",
    })
    items = {row["id"]: row for row in item_rows}
    answers = {row["item_id"]: row for row in result_rows}
    questions = []
    for link in links:
        item_id = link.get("item_id")
        saved = answers.get(item_id)
        item = items.get(item_id, {})
        if saved:
            questions.append({
                "itemId": item_id,
                "prompt": saved["prompt"],
                "options": saved.get("choices") or [],
                "answered": True,
                "studentAnswer": {"optionId": saved["choice_id"], "text": saved.get("choice_text")},
                "correctAnswer": {"optionId": saved["correct_option_id"], "text": saved.get("correct_answer_text")},
                "explanation": saved.get("explanation") or "",
                "correct": saved["correct"],
                "xpAwarded": saved["xp_awarded"],
            })
        else:
            questions.append({
                "itemId": item_id,
                "prompt": item.get("prompt"),
                "options": item.get("choices") or [],
                "answered": False,
                "studentAnswer": None,
                "correctAnswer": None,
                "explanation": None,
                "correct": None,
                "xpAwarded": 0,
            })

    answered = [row for row in result_rows]
    correct_count = sum(1 for row in answered if row.get("correct") is True)
    answered_count = len(answered)
    first = answered[0] if answered else None
    last = answered[-1] if answered else None
    return {
        "courseId": course_id,
        "setId": set_id,
        "score": {
            "correct": correct_count,
            "answered": answered_count,
            "total": len(links),
            "percent": round(100 * correct_count / answered_count, 1) if answered_count else None,
        },
        "totalXp": sum(int(row.get("xp_awarded") or 0) for row in answered),
        "masteryBefore": _mastery_display(
            float(first["mastery_before"]) if first and first.get("mastery_before") is not None else None,
            first.get("mastery_before_level") if first else None,
        ),
        "masteryAfter": _mastery_display(
            float(last["mastery_after"]) if last and last.get("mastery_after") is not None else None,
            last.get("mastery_after_level") if last else None,
        ),
        "questions": questions,
    }


@router.post("/{course_id}/submit")
def submit(
    request: Request,
    body: SubmitBody,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    handler_started = perf_counter_ns()
    timings: dict[str, float] = {"auth_ms": getattr(request.state, "practice_auth_ms", 0.0)}
    try:
        rows = db.rpc("submit_practice", {
            "p_institution_id": user.institution_id,
            "p_user_id": user.user_id,
            "p_course_id": course_id,
            "p_item_id": body.item_id,
            "p_choice_id": body.choice_id,
            "p_set_id": body.set_id,
            "p_session_id": str(body.session_id or body.set_id) if (body.session_id or body.set_id) else None,
            "p_idempotency_key": body.idempotency_key or str(uuid4()),
            "p_latency_ms": body.latency_ms,
        })
    except HTTPStatusError as exc:
        try:
            db_error = exc.response.json()
        except ValueError:
            db_error = {}
        if db_error.get("code") == "P0002":
            detail = "item is not in this set" if db_error.get("message") == "item is not in this set" else "item not found"
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail) from exc
        raise
    if not rows:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "could not record practice review")
    review_result = rows[0] if isinstance(rows, list) else rows
    for field in ("item_lookup_ms", "grading_ms", "set_membership_ms", "review_rpc_ms",
                  "attempts_ms", "exposure_ms"):
        timings[field] = float(review_result.get(field) or 0)
    timings["transactional_review_rpc_ms"] = timings["review_rpc_ms"]
    timings["xp_ms"] = 0.0  # XP is read separately; submit does not calculate it.
    response_started = perf_counter_ns()
    response = {
        "correct": review_result["correct"],
        "explanation": review_result["explanation"],
        "mastery": review_result.get("mastery_estimate"),
        "correctOptionId": review_result["correct_option_id"],
        "correctAnswerText": review_result.get("correct_answer_text"),
        "xpAwarded": int(review_result.get("xp_awarded") or 0),
        "masteryBefore": _mastery_display(
            float(review_result["mastery_before"]) if review_result.get("mastery_before") is not None else None,
            review_result.get("mastery_before_level"),
        ),
        "masteryAfter": _mastery_display(
            float(review_result["mastery_after"]) if review_result.get("mastery_after") is not None else None,
            review_result.get("mastery_after_level"),
        ),
    }
    timings["response_build_ms"] = (perf_counter_ns() - response_started) / 1_000_000
    timings["handler_ms"] = (perf_counter_ns() - handler_started) / 1_000_000
    request.state.practice_submit_timings = timings
    return response
