"""Student twin endpoints. The twin is the signature surface: per-skill
mastery (qualitative bands, numeric secondary), board readiness, and the
append-only evidence ledger. Reads are scoped to the calling student's own
state (RLS enforces the boundary; the API shapes the response)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.twin import summary

router = APIRouter(prefix="/courses", tags=["twin"])


@router.get("/{course_id}/twin")
def get_twin(course_id: str, user: CurrentUser = Depends(get_current_user)):
    return summary.twin_payload(
        institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
    )


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
