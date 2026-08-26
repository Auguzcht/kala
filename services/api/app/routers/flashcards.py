"""Flashcard endpoints. Quick review, not graded like the diagnostic or
practice loop: the student self-reports whether they knew it, which feeds
the tracer as a lighter-weight signal.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.twin import tracer

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/{course_id}/deck")
def deck(course_id: str, limit: int = 5, user: CurrentUser = Depends(get_current_user)):
    skills = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level", "limit": str(limit),
    })
    cards = [
        item_gen.generate_flashcard(
            institution_id=user.institution_id, course_id=course_id, skill=s,
        )
        for s in skills
    ]
    return {"courseId": course_id, "cards": cards}


class ReviewBody(BaseModel):
    item_id: str
    knew_it: bool
    latency_ms: int = 0


@router.post("/{course_id}/review")
def review(course_id: str, body: ReviewBody, user: CurrentUser = Depends(get_current_user)):
    rows = db.select("generated_items", {
        "id": f"eq.{body.item_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "id,skill_id", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    skill_id = rows[0]["skill_id"]

    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": skill_id, "type": "flashcard",
        "correct": body.knew_it, "latency_ms": body.latency_ms,
    }])
    tracer.apply_evidence(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id, correct=body.knew_it,
    )
    return {"ok": True}
