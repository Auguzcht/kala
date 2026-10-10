"""Board-exam readiness from mastery, weighted by the skill blueprint. Simple
weighted mean for September; refine with the exam blueprint later."""
from __future__ import annotations

from app.db import supabase as db


def compute(*, user_id: str, course_id: str) -> float:
    skills = db.select("skills", {
        "course_id": f"eq.{course_id}", "status": "eq.approved", "select": "id",
    })
    skill_ids = [s["id"] for s in skills]
    if not skill_ids:
        return 0.0
    rows = db.select("mastery_state", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "skill_id": f"in.({','.join(skill_ids)})",
        "select": "estimate",
    })
    if not rows:
        return 0.0
    return round(sum(float(r["estimate"]) for r in rows) / len(rows), 3)
