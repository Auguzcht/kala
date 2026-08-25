"""Diagnostic endpoints. Full path: ingest, read course skills, generate
RAG-grounded questions, accept answers, grade server-side, write evidence
(service role), update the twin.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai import bedrock, router as model_router
from app.ai.chunking import chunk_text
from app.ai.deidentify import strip_pii
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.learn import items as item_gen
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


class SubmitAnswer(BaseModel):
    item_id: str
    choice_id: str
    latency_ms: int = 0


class SubmitBody(BaseModel):
    answers: list[SubmitAnswer]


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
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "id,name,bloom_level", "limit": "10",
    })
    questions = [
        item_gen.generate_question(
            institution_id=user.institution_id, course_id=course_id,
            skill=s, kind="diagnostic",
        )
        for s in skills
    ]
    return {"courseId": course_id, "questions": questions}


@router.post("/{course_id}/diagnostic/submit")
def submit_diagnostic(course_id: str, body: SubmitBody,
                      user: CurrentUser = Depends(get_current_user)):
    results = []
    rows = []
    for a in body.answers:
        try:
            graded = item_gen.grade(
                institution_id=user.institution_id, item_id=a.item_id, choice_id=a.choice_id,
            )
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"item {a.item_id} not found")
        results.append({**graded, "itemId": a.item_id})
        rows.append({
            "institution_id": user.institution_id, "user_id": user.user_id,
            "course_id": course_id, "skill_id": graded["skillId"], "type": "diagnostic",
            "correct": graded["correct"], "latency_ms": a.latency_ms,
        })
    if rows:
        db.insert_evidence(rows)
    for r in results:
        tracer.apply_evidence(
            institution_id=user.institution_id, user_id=user.user_id,
            course_id=course_id, skill_id=r["skillId"], correct=r["correct"],
        )
    correct = sum(1 for r in results if r["correct"])
    return {
        "correctCount": correct,
        "total": len(results),
        "results": [{"itemId": r["itemId"], "correct": r["correct"], "explanation": r["explanation"]} for r in results],
    }
