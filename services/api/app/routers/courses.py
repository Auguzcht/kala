"""Course meta. Thin read of the LMS mirror; the LMS remains the content
system of record. Used by the app shell (top-bar breadcrumb, workspace
heading)."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, require_valid_course_id
from app.learn import srs
from app.routers import bank as bank_router
from app.routers.diagnostic import _assert_teaches_course, _course_ref

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/{course_id}")
def get_course(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    if user.app_role == "student":
        bank_router._course_for_user(course_id, user)
    if user.app_role in {"instructor", "admin"}:
        _assert_teaches_course(user=user, course_id=course_id)
        _course_ref(course_id, user.institution_id)
    rows = db.select("courses", {
        "id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "id,title,lms_course_id", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    row = rows[0]
    return {"id": row["id"], "title": row["title"], "lmsCourseId": row["lms_course_id"]}


@router.get("/{course_id}/memory/summary")
def memory_summary(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Per-skill card-memory counts. Reading the summary never creates SRS rows."""
    if user.app_role == "student":
        bank_router._course_for_user(course_id, user)
    if user.app_role in {"instructor", "admin"}:
        _assert_teaches_course(user=user, course_id=course_id)
        _course_ref(course_id, user.institution_id)
    skills = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved", "select": "id,name", "order": "name.asc", "limit": "1000",
    })
    by_skill = {skill["id"]: {
        "skillId": skill["id"], "skillName": skill["name"],
        "counts": {state: 0 for state in ("new", "learning", "slipping", "known")} | {"dueToday": 0},
    } for skill in skills}
    if not by_skill:
        return {"courseId": course_id, "skills": [], "totals": {
            "new": 0, "learning": 0, "slipping": 0, "known": 0, "dueToday": 0,
        }, "newRemainingToday": srs.new_remaining_today(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        )}

    items = db.select("generated_items", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "retired_at": "is.null", "or": "(and(kind.eq.practice,origin.eq.bank),kind.eq.flashcard)",
        "skills.status": "eq.approved",
        "select": "id,skill_id,skills!inner(status)", "limit": "10000",
    })
    item_ids = [item["id"] for item in items]
    schedules = db.select("srs_state", {
        "institution_id": f"eq.{user.institution_id}", "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}", "select": "item_id,skill_id,box,ease_milli,streak,reps,lapses,last_outcome,due_at",
        "limit": "10000",
    }) if item_ids else []
    eligible = set(item_ids)
    by_item = {row["item_id"]: row for row in schedules if row["item_id"] in eligible}
    institution = db.select("institutions", {
        "id": f"eq.{user.institution_id}", "select": "timezone", "limit": "1",
    })
    zone = ZoneInfo(institution[0].get("timezone") or "UTC") if institution else ZoneInfo("UTC")
    now = datetime.now(timezone.utc)
    day_end = datetime.combine(now.astimezone(zone).date() + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    for item in items:
        bucket = by_skill.get(item.get("skill_id"))
        if bucket is None:
            continue
        row = by_item.get(item["id"])
        state = "new" if row is None else srs.card_state(
            reps=int(row["reps"]), last_outcome=row.get("last_outcome"),
            lapses=int(row["lapses"]), box=int(row["box"]), ease_milli=int(row["ease_milli"]),
        )
        bucket["counts"][state] += 1
        due_at = datetime.fromisoformat(row["due_at"].replace("Z", "+00:00")) if row and row.get("due_at") else None
        if due_at is not None and due_at < day_end:
            bucket["counts"]["dueToday"] += 1
    totals = {key: sum(row["counts"][key] for row in by_skill.values())
              for key in ("new", "learning", "slipping", "known", "dueToday")}
    return {
        "courseId": course_id, "skills": list(by_skill.values()), "totals": totals,
        "newRemainingToday": srs.new_remaining_today(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }
