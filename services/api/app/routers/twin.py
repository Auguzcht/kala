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


@router.get("/{course_id}/plan")
def learning_plan(course_id: str, user: CurrentUser = Depends(get_current_user)):
    """What this learner's instructor has actually assigned them.

    The closing half of the human-in-the-loop loop. The instructor surface
    generates AI recommendations and decides on them; this endpoint is the
    only way a decided action reaches the learner. It filters on
    status in ('approved','modified') by design:

      suggested  -> the teacher has not looked yet. Invisible here. If a
                    learner could see un-decided AI output, the gate would
                    be decorative.
      rejected   -> the teacher declined it. Invisible here, kept in the
                    audit trail.
      completed  -> done, shown greyed so the learner can see their history.

    The learner sees the action and the instructor's note, never the
    model's confidence score or the raw evidence panel — those are
    instructor-facing framing about the learner, and handing a student
    "the model is 84% confident you are weak at IAM" is the exact thing
    the design brief rules out.
    """
    rows = db.select("recommendations", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "user_id": f"eq.{user.user_id}",
        "status": "in.(approved,modified,completed)",
        "select": "id,skill_id,title,action,kind,priority,status,instructor_note,decided_at,created_at",
        "order": "decided_at.desc", "limit": "20",
    })
    if not rows:
        return {"courseId": course_id, "plan": []}

    skills = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "select": "id,name",
    })
    names = {s["id"]: s["name"] for s in skills}

    return {
        "courseId": course_id,
        "plan": [{
            "id": r["id"],
            "title": r.get("title") or r.get("action") or "Next step",
            "kind": r.get("kind") or "practice",
            "priority": r.get("priority") or "medium",
            "status": r.get("status"),
            "skillId": r.get("skill_id"),
            "skillName": names.get(r.get("skill_id") or ""),
            "instructorNote": r.get("instructor_note"),
            "assignedAt": r.get("decided_at") or r.get("created_at"),
        } for r in rows],
    }
