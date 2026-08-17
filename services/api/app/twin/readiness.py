"""Board-exam readiness from mastery, weighted by the skill blueprint. Simple
weighted mean for September; refine with the exam blueprint later."""
from __future__ import annotations

from app.db import supabase as db


def compute(*, user_id: str, course_id: str) -> float:
    rows = db.select("mastery_state", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "estimate",
    })
    if not rows:
        return 0.0
    return round(sum(float(r["estimate"]) for r in rows) / len(rows), 3)
