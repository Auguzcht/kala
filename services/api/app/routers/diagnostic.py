"""Diagnostic endpoints. Worked example of the full path: read course skills,
serve questions, accept answers, write evidence (service role), update the twin.
Question generation from LMS content via RAG is the next step (marked TODO)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai import bedrock, router as model_router
from app.ai.chunking import chunk_text
from app.ai.deidentify import strip_pii
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.lms.blackboard import BlackboardConnector
from app.twin import tracer

router = APIRouter(prefix="/courses", tags=["diagnostic"])


def _course_ref(course_id: str, institution_id: str) -> str:
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{institution_id}",
        "select": "lms_course_id",
        "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    return courses[0]["lms_course_id"]


@router.get("/{course_id}/roster")
def get_roster(course_id: str,
               user: CurrentUser = Depends(get_current_user),
               connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_roster(_course_ref(course_id, user.institution_id))


@router.get("/{course_id}/content")
def get_content(course_id: str,
                user: CurrentUser = Depends(get_current_user),
                connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_content(_course_ref(course_id, user.institution_id))


@router.get("/{course_id}/assessments")
def get_assessments(course_id: str,
                    user: CurrentUser = Depends(get_current_user),
                    connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_assessments(_course_ref(course_id, user.institution_id))


@router.post("/{course_id}/ingest")
def ingest_course(course_id: str,
                  user: CurrentUser = Depends(get_current_user),
                  connector: BlackboardConnector = Depends(get_lms_connector)):
    course_ref = _course_ref(course_id, user.institution_id)
    skills = db.select("skills", {
        "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "id,name",
    })
    content_items = connector.get_content(course_ref)
    stored = 0
    tagged = 0
    embedded = 0

    for item in content_items:
        body = item.get("body_or_description", "")
        if not body:
            continue
        for chunk in chunk_text(body):
            clean_chunk = strip_pii(chunk)
            rows = db.insert("content_items", [{
                "institution_id": user.institution_id,
                "course_id": course_id,
                "lms_ref": item.get("lms_content_id"),
                "chunk_text": clean_chunk,
            }])
            if not rows:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "content row was not stored")
            row_id = rows[0]["id"]
            stored += 1

            tag = model_router.tag_content(text=clean_chunk, skills=skills)
            values = {}
            if tag["skill_id"]:
                values["skill_id"] = tag["skill_id"]
                tagged += 1
            if values:
                db.update("content_items", {"id": f"eq.{row_id}"}, values)

            embedding = bedrock.embed(clean_chunk)
            if len(embedding) != 1024:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    f"embedding dimension was {len(embedding)}, expected 1024",
                )
            db.update("content_items", {"id": f"eq.{row_id}"}, {"embedding": embedding})
            embedded += 1

    return {"stored": stored, "tagged": tagged, "embedded": embedded}


class Answer(BaseModel):
    question_id: str
    skill_id: str
    correct: bool
    latency_ms: int = 0


class SubmitBody(BaseModel):
    answers: list[Answer]


class GradeBody(BaseModel):
    user_id: str
    score: float


@router.patch("/{course_id}/assessments/{column_id}/grade")
def post_grade(course_id: str, column_id: str, body: GradeBody,
               user: CurrentUser = Depends(get_current_user),
               connector: BlackboardConnector = Depends(get_lms_connector)):
    connector.post_grade(
        _course_ref(course_id, user.institution_id),
        column_id,
        body.user_id,
        body.score,
    )
    return {"courseId": course_id, "columnId": column_id, "userId": body.user_id, "score": body.score}


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
