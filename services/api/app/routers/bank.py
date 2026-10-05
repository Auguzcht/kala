"""Student/staff-safe bank build status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.bank.kick import kick_bank
from app.bank.serving import MIN_USABLE, bank_enabled
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, require_valid_course_id

router = APIRouter(prefix="/courses", tags=["bank"])


def _course_for_user(course_id: str, user: CurrentUser) -> dict:
    rows = db.select("courses", {"id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}", "select": "id,institution_id,bank_serving", "limit": "1"})
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    if user.app_role in {"instructor", "admin"}:
        return rows[0]
    enrolled = db.select("enrollments", {"course_id": f"eq.{course_id}", "user_id": f"eq.{user.user_id}", "select": "user_id", "limit": "1"})
    if not enrolled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    return rows[0]


@router.get("/{course_id}/bank/status")
def bank_status(course_id: str = Depends(require_valid_course_id), user: CurrentUser = Depends(get_current_user)):
    course = _course_for_user(course_id, user)
    fields = "skill_id,status,mcq_ready,mcq_target,depth"
    if user.app_role in {"instructor", "admin"}:
        fields += ",last_error"
    rows = db.select("skill_bank_state", {"course_id": f"eq.{course_id}", "select": fields, "order": "skill_id.asc"})
    skills = []
    for row in rows:
        usable = int(row.get("mcq_ready") or 0) >= MIN_USABLE
        item = {"skillId": row["skill_id"], "status": row.get("status"), "mcqReady": row.get("mcq_ready", 0),
                "mcqTarget": row.get("mcq_target", 0), "depth": row.get("depth", 0), "usable": usable}
        if user.app_role in {"instructor", "admin"} and "last_error" in row:
            item["lastError"] = row.get("last_error")
        skills.append(item)
    if any(not row["usable"] for row in skills):
        pending = db.select("skill_bank_state", {"course_id": f"eq.{course_id}", "status": "not.in.(ready,no_material)", "leased_until": "is.null", "next_attempt_at": "is.null", "select": "skill_id", "limit": "1"})
        if pending:
            kick_bank(course_id, "status")
    return {"courseId": course_id, "building": any(
                row["status"] not in {"ready", "no_material"} and not row["usable"]
                for row in skills
            ), "skills": skills,
            "bankServing": bank_enabled(course, "study")}
