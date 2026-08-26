"""Student twin endpoints. The twin is the signature surface: per-skill
mastery (as qualitative bands, numeric secondary), board readiness, and the
append-only evidence ledger. Reads are scoped to the calling student's own
state (RLS enforces the boundary; the API shapes the response)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.twin import readiness

router = APIRouter(prefix="/courses", tags=["twin"])

# Qualitative mastery bands, neutral-to-gold. Red never enters this scale;
# it belongs to the at-risk axis (instructor surface, a different object).
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


def _skills_with_mastery(*, institution_id: str, user_id: str, course_id: str) -> list[dict]:
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
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


@router.get("/{course_id}/twin")
def get_twin(course_id: str, user: CurrentUser = Depends(get_current_user)):
    skills = _skills_with_mastery(
        institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
    )
    if not skills:
        return {"courseId": course_id, "readiness": None, "skills": [], "evidence": []}

    events = db.select("evidence_events", {
        "user_id": f"eq.{user.user_id}", "course_id": f"eq.{course_id}",
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
        "readiness": readiness.compute(user_id=user.user_id, course_id=course_id),
        "skills": skills,
        "evidence": evidence,
    }


@router.get("/{course_id}/next-up")
def next_up(course_id: str, user: CurrentUser = Depends(get_current_user)):
    """One recommendation: the skill this student should practice next.
    Lightweight — reuses the same weakest-skill picker as practice but does
    not generate an item (that happens when they actually start)."""
    skill = item_gen.weakest_skill(
        institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
    )
    if not skill:
        return {"courseId": course_id, "next": None}

    estimates = db.select("mastery_state", {
        "institution_id": f"eq.{user.institution_id}", "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate",
    })
    estimate = next((float(e["estimate"]) for e in estimates if e["skill_id"] == skill["id"]), None)
    reason = (
        "your least-practiced skill — a good place to build your baseline"
        if estimate is None
        else "your lowest mastery right now — practice moves the needle most here"
    )
    return {
        "courseId": course_id,
        "next": {
            "skillId": skill["id"],
            "skillName": skill["name"],
            "bloomLevel": skill.get("bloom_level"),
            "kind": "practice",
            "reason": reason,
            "estimate": estimate,
        },
    }
