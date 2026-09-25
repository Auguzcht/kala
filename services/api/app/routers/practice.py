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
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import supabase as db
from app.deps import (
    CurrentUser,
    get_current_user,
    require_valid_course_id,
    require_valid_set_id,
)
from app.learn import items as item_gen
from app.routers.item_generation_jobs import enqueue_practice, practice_jobs
from app.twin import tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/practice", tags=["practice"])

# One sitting's worth of practice questions. Bounded so a set is a set, not an
# unbounded generation fan-out: N items means N concurrent model calls (see
# ai/concurrency.py), and this keeps that fan-out inside one request's budget.
MAX_SET_SIZE = 10
DEFAULT_SET_SIZE = 5


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


def _practice_set_view(
    *, course_id: str, set_row: dict, jobs: list[dict], items: list[dict],
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
    status_value = (
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
    size = min(size, MAX_SET_SIZE)

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
        "select": "id,skill_id,prompt,choices,bloom_level",
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

    # Attach the existing items to the set. This is the one place a set is
    # built by re-pointing rows rather than inserting them — safe because
    # set_id is a delivery grouping, not part of the answer key.
    for item in ordered:
        db.update("generated_items", {"id": f"eq.{item['id']}"}, {"set_id": set_id})

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
    rows = db.select("generated_items", {
        "set_id": f"in.({','.join(set_ids)})",
        "institution_id": f"eq.{institution_id}",
        "select": "set_id",
    })
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

    items = db.select("generated_items", {
        "set_id": f"eq.{set_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "id,skill_id,prompt,choices,bloom_level",
        "order": "created_at.asc",
    })
    jobs = practice_jobs(
        institution_id=user.institution_id, course_id=course_id, set_id=set_id,
    )
    s = sets[0]
    attempts = _attempts_by_set(
        institution_id=user.institution_id, user_id=user.user_id, set_ids=[s["id"]],
    )
    return {
        **_practice_set_view(course_id=course_id, set_row=s, jobs=jobs, items=items),
        **_attempt_view(attempts.get(s["id"])),
    }


def _record_set_attempt(*, institution_id: str, user_id: str, course_id: str,
                        set_id: str, correct: bool) -> None:
    """Increment this student's counters for a set they just answered in.

    Read-then-upsert rather than a single atomic increment: PostgREST has no
    increment operator, so the new totals are computed here against the
    current row and written back on the (user_id, set_id) conflict target. A
    single student answers a set one question at a time, so there is no
    meaningful concurrent-writer race in practice; if that ever changes, this
    is the function that becomes an RPC.

    This is intentionally separate from the evidence/tracer writes in
    submit() — those are the mastery signal, this is just "did you take this
    set and how did you do", and neither depends on the other.
    """
    existing = db.select("quiz_set_attempts", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "set_id": f"eq.{set_id}",
        "select": "attempted_count,correct_count", "limit": "1",
    })
    attempted = (int(existing[0]["attempted_count"]) if existing else 0) + 1
    correct_count = (int(existing[0]["correct_count"]) if existing else 0) + (1 if correct else 0)
    db.upsert("quiz_set_attempts", [{
        "institution_id": institution_id, "user_id": user_id,
        "course_id": course_id, "set_id": set_id,
        "attempted_count": attempted, "correct_count": correct_count,
        "last_attempted_at": datetime.now(timezone.utc).isoformat(),
    }], on_conflict="user_id,set_id")


@router.post("/{course_id}/submit")
def submit(
    body: SubmitBody,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        graded = item_gen.grade(
            institution_id=user.institution_id, item_id=body.item_id, choice_id=body.choice_id,
        )
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found")

    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": graded["skillId"], "type": "practice",
        "correct": graded["correct"], "latency_ms": body.latency_ms,
    }])
    state = tracer.apply_evidence(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=graded["skillId"], correct=graded["correct"],
    )
    # Attempt bookkeeping for a grouped item. An ungrouped item (/next, no
    # set) has setId null and touches nothing here — same as it touches
    # nothing in quiz_sets. Grading, evidence, and mastery above are all
    # unchanged; this is purely the per-student "have I taken this set"
    # counter the Test tab badge reads.
    if graded.get("setId"):
        _record_set_attempt(
            institution_id=user.institution_id, user_id=user.user_id,
            course_id=course_id, set_id=graded["setId"], correct=graded["correct"],
        )
    return {
        "correct": graded["correct"],
        "explanation": graded["explanation"],
        "mastery": state.get("estimate"),
    }
