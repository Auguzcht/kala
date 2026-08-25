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
def next_item(course_id: str, user: CurrentUser = Depends(get_current_user)):
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
