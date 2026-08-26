"""Shared twin payload builder. One shape for two doors: the student's own
twin (/courses/{id}/twin) and the instructor's per-student drill-down
(/dashboard/{course_id}/students/{user_id}/twin). The client never computes
mastery; bands are derived here, neutral-to-gold, numeric estimate
secondary."""
from __future__ import annotations

from app.db import supabase as db
from app.twin import readiness

_BANDS = [
    (0.4, "developing"),
    (0.7, "proficient"),
    (1.01, "mastered"),
]


def band_for(estimate: float | None) -> str:
    if estimate is None:
        return "no-evidence"
    for threshold, band in _BANDS:
        if estimate < threshold:
            return band
    return "mastered"


def skills_with_mastery(*, institution_id: str, user_id: str, course_id: str) -> list[dict]:
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",  # never surface unreviewed proposals to a learner
        "select": "id,name,bloom_level", "order": "name.asc",
    })
    if not skills:
        return []
    mastery = db.select("mastery_state", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate,attempts",
    })
    estimates = {m["skill_id"]: m for m in mastery}
    return [{
        "skillId": s["id"],
        "name": s["name"],
        "bloomLevel": s["bloom_level"],
        "estimate": float(estimates[s["id"]]["estimate"]) if s["id"] in estimates else None,
        "attempts": int(estimates[s["id"]]["attempts"]) if s["id"] in estimates else 0,
        "band": band_for(float(estimates[s["id"]]["estimate"]) if s["id"] in estimates else None),
    } for s in skills]


def twin_payload(*, institution_id: str, user_id: str, course_id: str) -> dict:
    """The twin response shape: skills + bands, readiness, evidence ledger."""
    skills = skills_with_mastery(
        institution_id=institution_id, user_id=user_id, course_id=course_id,
    )
    if not skills:
        return {"courseId": course_id, "readiness": None, "skills": [], "evidence": []}

    events = db.select("evidence_events", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "id,skill_id,type,correct,latency_ms,created_at",
        "order": "created_at.desc", "limit": "20",
    })
    by_skill = {s["skillId"]: s["name"] for s in skills}
    evidence = [{
        "id": e["id"],
        "type": e["type"],
        "correct": e["correct"],
        "latencyMs": e.get("latency_ms"),
        "skillName": by_skill.get(e.get("skill_id"), "Unknown skill"),
        "createdAt": e.get("created_at"),
    } for e in events]

    return {
        "courseId": course_id,
        "readiness": readiness.compute(user_id=user_id, course_id=course_id),
        "skills": skills,
        "evidence": evidence,
    }
