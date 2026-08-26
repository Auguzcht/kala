"""Instructor dashboard. Cohort analytics scoped to the caller's course:
skills-by-Bloom's heatmap (students × skills), the needs-support list
(evidence-triggered, supportive wording — never a verdict), and the
per-student twin drill-down. RLS enforces the boundary; the API shapes it.

Students see pseudonyms here, never LMS names: this surface can reach a
model and it is the research-facing read, so the de-identification posture
is explicit (the UI shows the "de-identified" chip, not a backend footnote).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import supabase as db
from app.deps import CurrentUser, require_role
from app.twin import summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

INACTIVE_AFTER_DAYS = 7
LOW_SUCCESS_ATTEMPTS = 5
LOW_SUCCESS_RATE = 0.4


def _cohort(*, institution_id: str, course_id: str) -> tuple[list[dict], list[dict], dict]:
    """skills, students (pseudonym + initials), and the per-user/per-skill
    mastery map. Two selects: enrollments→users, mastery_state."""
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "select": "id,name,bloom_level", "order": "name.asc",
    })
    enrollments = db.select("enrollments", {
        "course_id": f"eq.{course_id}", "role": "eq.student",
        "select": "user_id", "order": "user_id.asc",
    })
    user_ids = [e["user_id"] for e in enrollments]
    students: list[dict] = []
    if user_ids:
        users = db.select("users", {
            "id": f"in.({','.join(user_ids)})", "institution_id": f"eq.{institution_id}",
            "select": "id,pseudonym",
        })
        by_id = {u["id"]: u["pseudonym"] for u in users}
        for uid in user_ids:
            pseudonym = by_id.get(uid, "Student")
            students.append({
                "userId": uid,
                "pseudonym": pseudonym,
                "initials": "".join(p[0] for p in pseudonym.split()[:2]).upper() or "?",
            })

    cells: dict[tuple[str, str], dict] = {}
    if user_ids:
        mastery = db.select("mastery_state", {
            "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
            "user_id": f"in.({','.join(user_ids)})",
            "select": "user_id,skill_id,estimate,attempts",
        })
        for m in mastery:
            cells[(m["user_id"], m["skill_id"])] = m
    return skills, students, cells


def _band_cell(m: dict | None) -> dict:
    estimate = float(m["estimate"]) if m else None
    return {
        "estimate": estimate,
        "attempts": int(m["attempts"]) if m else 0,
        "band": summary.band_for(estimate),
    }


@router.get("/{course_id}/heatmap")
def heatmap(course_id: str, user: CurrentUser = Depends(require_role("instructor", "admin"))):
    skills, students, cells = _cohort(
        institution_id=user.institution_id, course_id=course_id,
    )

    # Per-skill cohort band + per-student rollup (readiness proxy) from the
    # same cells, no extra queries.
    skill_rows = []
    cohort_readiness_values: list[float] = []
    for s in skills:
        estimates = [
            float(cells[(u["userId"], s["id"])]["estimate"])
            for u in students
            if (u["userId"], s["id"]) in cells
        ]
        cohort = (sum(estimates) / len(estimates)) if estimates else None
        skill_rows.append({
            "skillId": s["id"],
            "name": s["name"],
            "bloomLevel": s["bloom_level"],
            "cohortBand": summary.band_for(cohort),
            "cohortEstimate": cohort,
        })
        if cohort is not None:
            cohort_readiness_values.append(cohort)

    cell_rows = [{
        "userId": u["userId"],
        "skillId": s["skillId"],
        **_band_cell(cells.get((u["userId"], s["skillId"]))),
    } for u in students for s in skill_rows]

    return {
        "courseId": course_id,
        "cohortReadiness": (
            round(sum(cohort_readiness_values) / len(cohort_readiness_values), 3)
            if cohort_readiness_values else None
        ),
        "skills": skill_rows,
        "students": students,
        "cells": cell_rows,
    }


def _student_evidence(*, institution_id: str, course_id: str, user_ids: list[str]) -> dict[str, list[dict]]:
    if not user_ids:
        return {}
    rows = db.select("evidence_events", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "user_id": f"in.({','.join(user_ids)})",
        "select": "user_id,skill_id,type,correct,created_at", "order": "created_at.desc",
        "limit": "500",
    })
    by_user: dict[str, list[dict]] = {}
    for r in rows:
        by_user.setdefault(r["user_id"], []).append(r)
    return by_user


def _days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        from datetime import datetime, timezone
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - then).days)
    except ValueError:
        return None


def _reason_for(*, evidence: list[dict], weakest: list[tuple[str, float | None]],
                days_inactive: int | None) -> str | None:
    """Supportive, evidence-triggered wording. Never a verdict on the
    student — a prompt to reach out (see the design brief guardrails)."""
    if not evidence:
        return "No evidence yet — hasn't started the diagnostic. A first practice session builds the baseline."
    correct = sum(1 for e in evidence if e.get("correct"))
    attempts = len(evidence)
    if days_inactive is not None and days_inactive >= INACTIVE_AFTER_DAYS:
        inactive = f"No activity in {days_inactive} days"
        if attempts >= LOW_SUCCESS_ATTEMPTS and (correct / attempts) < LOW_SUCCESS_RATE:
            return f"{inactive}, and a low success rate across the last {attempts} attempts."
        return f"{inactive}. A short practice session would re-anchor the material."
    if attempts >= LOW_SUCCESS_ATTEMPTS and (correct / attempts) < LOW_SUCCESS_RATE:
        return f"Low success rate across the last {attempts} attempts — practice is building gaps, not closing them. A tutor session on the weakest skill would help."
    low = [name for name, est in weakest[:2] if est is not None and est < 0.4]
    if len(low) >= 2:
        return f"Low mastery on {', '.join(low)}. A focused practice round on those skills moves the needle most."
    return None


@router.get("/{course_id}/at-risk")
def at_risk(course_id: str, user: CurrentUser = Depends(require_role("instructor", "admin"))):
    skills, students, cells = _cohort(
        institution_id=user.institution_id, course_id=course_id,
    )
    user_ids = [u["userId"] for u in students]
    evidence = _student_evidence(
        institution_id=user.institution_id, course_id=course_id, user_ids=user_ids,
    )
    skill_names = {s["id"]: s["name"] for s in skills}

    flags = []
    for u in students:
        ev = evidence.get(u["userId"], [])
        days = _days_since(ev[0]["created_at"]) if ev else None
        weakest = sorted(
            ((skill_names[s["id"]], cells[(u["userId"], s["id"])]["estimate"])
             if (u["userId"], s["id"]) in cells else (skill_names[s["id"]], None))
            for s in skills
        )
        weakest.sort(key=lambda t: (t[1] is not None, t[1] if t[1] is not None else -1.0))
        reason = _reason_for(evidence=ev, weakest=weakest, days_inactive=days)
        if reason is None:
            continue
        flags.append({
            "userId": u["userId"],
            "pseudonym": u["pseudonym"],
            "initials": u["initials"],
            "reason": reason,
            "daysInactive": days,
            "evidenceCount": len(ev),
            "weakestSkillNames": [name for name, _ in weakest[:3]],
        })

    flags.sort(key=lambda f: (f["daysInactive"] is None, -(f["daysInactive"] or 0)))
    return {"courseId": course_id, "flags": flags}


@router.get("/{course_id}/students/{user_id}/twin")
def student_twin(course_id: str, user_id: str,
                 user: CurrentUser = Depends(require_role("instructor", "admin"))):
    rows = db.select("users", {
        "id": f"eq.{user_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "pseudonym", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found")
    twin = summary.twin_payload(
        institution_id=user.institution_id, user_id=user_id, course_id=course_id,
    )
    twin["pseudonym"] = rows[0]["pseudonym"]
    return twin
