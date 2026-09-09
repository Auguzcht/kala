"""Practice endpoints. Mirrors the diagnostic path: pick the weakest skill
for this student, generate a fresh RAG-grounded item against real course
content, grade it server-side, write evidence, and roll the result into the
mastery tracer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.twin import tracer

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/{course_id}/next")
def next_item(
    course_id: str,
    skill_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    if skill_id:
        # Explicit topic choice from the picker — validate it's a real,
        # approved skill in THIS course before generating against it. The
        # weakest-skill path below never needs this check because it's
        # derived server-side from the course's own approved skills; this
        # path takes a client-supplied id and must not trust it blindly.
        rows = db.select("skills", {
            "id": f"eq.{skill_id}", "course_id": f"eq.{course_id}",
            "institution_id": f"eq.{user.institution_id}", "status": "eq.approved",
            "select": "id,name,bloom_level", "limit": "1",
        })
        skill = rows[0] if rows else None
        if not skill:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found")
    else:
        skill = item_gen.weakest_skill(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        )
    if not skill:
        return {"courseId": course_id, "item": None}
    item = item_gen.generate_question(
        institution_id=user.institution_id, course_id=course_id,
        skill=skill, kind="practice",
    )
    return {"courseId": course_id, "item": item}


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
