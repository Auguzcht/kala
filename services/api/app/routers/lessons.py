"""Guided lesson endpoints — the persistent step-by-step tutor.

GET  /lessons/{course_id}/skill/{skill_id}   generate-once (then replay) the
                                             guided lesson for a skill.
POST /lessons/{course_id}/steps/{step_id}/check   grade a step's comprehension
                                             check; passing writes a tutor
                                             evidence_event and moves the twin.

The lesson is grounded in real course content and generated on first open,
then stored. The comprehension check is a normal server-graded MCQ, so the
guided tutor is a mastery source, not just reading material.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.learn import lessons, srs, xp
from app.twin import tracer

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/{course_id}/skill/{skill_id}")
def get_lesson(course_id: str, skill_id: str, user: CurrentUser = Depends(get_current_user)):
    """Load the skill's guided lesson, generating and persisting it on first
    request. Idempotent thereafter."""
    skills = db.select("skills", {
        "id": f"eq.{skill_id}", "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}", "status": "eq.approved",
        "select": "id,name,bloom_level,module_ref", "limit": "1",
    })
    if not skills:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found or not approved")
    lesson = lessons.get_or_generate_lesson(
        institution_id=user.institution_id, course_id=course_id, skill=skills[0],
    )
    return lesson


class CheckBody(BaseModel):
    item_id: str
    choice_id: str
    latency_ms: int = 0
    hints_used: int = 0


@router.post("/{course_id}/steps/{step_id}/check")
def submit_check(course_id: str, step_id: str, body: CheckBody,
                 user: CurrentUser = Depends(get_current_user)):
    """Grade a step's comprehension check server-side. The step advances (the
    read -> understand -> apply gate) only when the client sees correct=True.
    A pass writes a tutor evidence_event and moves the tracer; the schedule is
    seeded too so a checked concept enters spaced review like any other card.

    Ownership is verified in two independent steps before anything is
    written, because the URL's course_id is caller-supplied and must not be
    trusted on its own:
      1. the step -> its lesson_id (a step id + check_item_id is not, by
         itself, proof the step belongs to THIS course);
      2. that lesson_id -> its lesson row, filtered by course_id AND
         institution_id from the path. Only then is the step known to
         actually belong here, closing the hole where a client could submit
         /lessons/COURSE_B/steps/{step-from-course-A}/check and have
         evidence + mastery written against COURSE_B using a check item that
         was never generated for it.
    """
    steps = db.select("guided_lesson_steps", {
        "id": f"eq.{step_id}", "check_item_id": f"eq.{body.item_id}",
        "select": "id,lesson_id,check_item_id", "limit": "1",
    })
    if not steps:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such check for this step")

    owned = db.select("guided_lessons", {
        "id": f"eq.{steps[0]['lesson_id']}",
        "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "id", "limit": "1",
    })
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such check for this step")

    try:
        graded = item_gen.grade(
            institution_id=user.institution_id, item_id=body.item_id, choice_id=body.choice_id,
        )
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "check item not found")

    # Defense in depth: the item's own course must also match the path, even
    # though the lesson-ownership check above should already guarantee it.
    if graded["courseId"] != course_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such check for this step")

    skill_id = graded["skillId"]
    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": skill_id, "type": "tutor",
        "correct": graded["correct"], "latency_ms": body.latency_ms,
        "hints_used": body.hints_used,
    }])
    state = tracer.apply_evidence(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id, correct=graded["correct"],
    )
    srs.review(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, item_id=body.item_id, skill_id=skill_id,
        correct=graded["correct"],
    )

    return {
        "correct": graded["correct"],
        "explanation": graded["explanation"],
        "advance": graded["correct"],
        "mastery": state.get("estimate"),
        "reward": xp.summary(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }
