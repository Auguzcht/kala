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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai.concurrency import map_concurrent
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.twin import tracer

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


@router.get("/{course_id}/next")
def next_item(
    course_id: str,
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


@router.post("/{course_id}/set")
def create_set(
    course_id: str,
    skill_id: str | None = None,
    size: int = DEFAULT_SET_SIZE,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a batch of practice items for ONE skill and group them under a
    quiz_sets row. This is the batch replacement for calling /next N times.

    The set row is created FIRST (status-free — it's just a grouping) so each
    generate_question call can write its set_id at insert time; an item is
    therefore never briefly persisted outside the set it belongs to. If every
    generation call fails, the empty set row is cleaned up rather than left as
    a dangling grouping with no items.

    A POST, not a GET: this has a side effect (persists N items), so it must
    not be cached or prefetched like the read-shaped /next is.
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
        return {"courseId": course_id, "setId": None, "items": []}

    set_rows = db.insert("quiz_sets", [{
        "institution_id": user.institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "kind": "practice",
        "size": size,
    }])
    set_id = set_rows[0]["id"]

    try:
        # N independent model calls for the SAME skill, run concurrently —
        # mirrors flashcards.py's deck top-up, just fanning out over items for
        # one skill instead of over distinct skills. Order is preserved by
        # map_concurrent, and each result comes back already persisted.
        items = map_concurrent(
            lambda _: item_gen.generate_question(
                institution_id=user.institution_id, course_id=course_id,
                skill=skill, kind="practice", set_id=set_id,
            ),
            list(range(size)),
        )
    except Exception:
        # Any failure (a model outage surfacing as ItemGenerationError, or a
        # DB error) leaves a set with fewer items than promised. Delete the
        # grouping so it doesn't linger as an empty/partial set; the items
        # already inserted cascade away with it. Re-raise so the error maps
        # to the same 502 the single-item path produces.
        db.delete("quiz_sets", {"id": f"eq.{set_id}"})
        raise

    return {"courseId": course_id, "setId": set_id, "items": items}


class SubmitBody(BaseModel):
    item_id: str
    choice_id: str
    latency_ms: int = 0


@router.post("/{course_id}/submit")
def submit(course_id: str, body: SubmitBody, user: CurrentUser = Depends(get_current_user)):
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
    return {
        "correct": graded["correct"],
        "explanation": graded["explanation"],
        "mastery": state.get("estimate"),
    }
