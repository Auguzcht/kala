"""Diagnostic endpoints. Worked example of the full path: read course skills,
serve questions, accept answers, write evidence (service role), update the twin.
Question generation from LMS content via RAG is the next step (marked TODO)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.twin import tracer

router = APIRouter(prefix="/courses", tags=["diagnostic"])


class Answer(BaseModel):
    question_id: str
    skill_id: str
    correct: bool
    latency_ms: int = 0


class SubmitBody(BaseModel):
    answers: list[Answer]


@router.get("/{course_id}/diagnostic")
def get_diagnostic(course_id: str, user: CurrentUser = Depends(get_current_user)):
    skills = db.select("skills", {
        "course_id": f"eq.{course_id}", "select": "id,name,bloom_level", "limit": "10",
    })
    # TODO: generate real, course-grounded questions via app.ai.rag + router.
    questions = [{
        "id": f"q-{s['id']}",
        "skillId": s["id"],
        "bloomLevel": s["bloom_level"],
        "prompt": f"Placeholder question for {s['name']}",
        "choices": [{"id": "a", "label": "Option A"}, {"id": "b", "label": "Option B"}],
    } for s in skills]
    return {"courseId": course_id, "questions": questions}


@router.post("/{course_id}/diagnostic/submit")
def submit_diagnostic(course_id: str, body: SubmitBody,
                      user: CurrentUser = Depends(get_current_user)):
    rows = [{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": a.skill_id, "type": "diagnostic",
        "correct": a.correct, "latency_ms": a.latency_ms,
    } for a in body.answers]
    if rows:
        db.insert_evidence(rows)
    for a in body.answers:
        tracer.apply_evidence(
            institution_id=user.institution_id, user_id=user.user_id,
            course_id=course_id, skill_id=a.skill_id, correct=a.correct,
        )
    correct = sum(1 for a in body.answers if a.correct)
    return {"correctCount": correct, "total": len(body.answers)}
