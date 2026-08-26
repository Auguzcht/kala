"""Course meta. Thin read of the LMS mirror; the LMS remains the content
system of record. Used by the app shell (top-bar breadcrumb, workspace
heading)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/{course_id}")
def get_course(course_id: str, user: CurrentUser = Depends(get_current_user)):
    rows = db.select("courses", {
        "id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "id,title,lms_course_id", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    row = rows[0]
    return {"id": row["id"], "title": row["title"], "lmsCourseId": row["lms_course_id"]}
