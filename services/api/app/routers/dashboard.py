"""Instructor dashboard. Cohort analytics scoped to the caller's course:
skills-by-Bloom's heatmap (students × skills), the needs-support list
(evidence-triggered, supportive wording — never a verdict), and the
per-student twin drill-down. RLS enforces the boundary; the API shapes it.

Students see pseudonyms here, never LMS names: this surface can reach a
model and it is the research-facing read, so the de-identification posture
is explicit (the UI shows the "de-identified" chip, not a backend footnote).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai import prescriber
from app.db import supabase as db
from app.deps import CurrentUser, require_role
from app.twin import cohort, summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

INACTIVE_AFTER_DAYS = 7
LOW_SUCCESS_ATTEMPTS = 5
LOW_SUCCESS_RATE = 0.4


def _cohort(
    *, institution_id: str, course_id: str, module_ref: str | None = None,
) -> tuple[list[dict], list[dict], dict]:
    """skills, students (pseudonym + initials), and the per-user/per-skill
    mastery map. Two selects: enrollments→users, mastery_state.

    module_ref is optional and generic: any institution whose ingest has
    populated skills.module_ref (see lms/hierarchy.py) can filter by it,
    nothing here assumes what a "module" means for a given school. Omitted,
    behavior is unchanged, the whole course's skills are returned."""
    skill_filters = {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",  # heatmap shows reviewed skills only
        "select": "id,name,bloom_level", "order": "name.asc",
    }
    if module_ref is not None:
        skill_filters["module_ref"] = f"eq.{module_ref}"
    skills = db.select("skills", skill_filters)
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
def heatmap(
    course_id: str,
    module_ref: str | None = None,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    skills, students, cells = _cohort(
        institution_id=user.institution_id, course_id=course_id, module_ref=module_ref,
    )

    # The roster and at-risk list resolved real names via load_identities;
    # the heatmap used to ship raw pseudonyms because _cohort only selects
    # them. Same lookup, same placeholder guard — a teacher reading the
    # heatmap should see the same names as the roster beside it.
    names = cohort.load_identities(
        institution_id=user.institution_id,
        user_ids=[u["userId"] for u in students],
    )
    for u in students:
        ident = names.get(u["userId"], {})
        u["displayName"] = ident.get("displayName") or u["pseudonym"]

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
        cohort_avg = (sum(estimates) / len(estimates)) if estimates else None
        skill_rows.append({
            "skillId": s["id"],
            "name": s["name"],
            "bloomLevel": s["bloom_level"],
            "cohortBand": summary.band_for(cohort_avg),
            "cohortEstimate": cohort_avg,
        })
        if cohort_avg is not None:
            cohort_readiness_values.append(cohort_avg)

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
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - then).days)
    except ValueError:
        return None


def _reason_for(*, evidence: list[dict], weakest: list[tuple[str, float | None]],
                days_inactive: int | None) -> str | None:
    """Supportive, evidence-triggered wording. Never a verdict on the
    student — a prompt to reach out (see the design brief guardrails).

    Deliberately NOT triggered by zero evidence: a student who has never
    started is triaged by the roster's own 'not-started' status (a nudge
    to begin, not a support concern — see cohort._status_for, which keeps
    the two buckets separate on purpose). Flagging every fresh enrollment
    as 'needs support' would also break the roster handoff: the at-risk
    list's 'View all in roster' switches to the needs-support filter, and
    not-started students never match it, landing on an empty table.
    """
    if not evidence:
        return None
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
    # This route pre-dates the roster/stats rework and only ever selected
    # pseudonym. cohort.load_identities is the same lookup the roster and
    # learner record now use, so a name shown here matches what the teacher
    # sees everywhere else instead of falling back to "anon-xxxx".
    names = cohort.load_identities(institution_id=user.institution_id, user_ids=user_ids)

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
        ident = names.get(u["userId"], {})
        flags.append({
            "userId": u["userId"],
            "displayName": ident.get("displayName") or u["pseudonym"],
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


# ---- Skill proposal review (human-in-the-loop gate) -----------------------
# AI proposes skills on course launch (see ai/skill_proposer.py); nothing
# proposed reaches the twin/heatmap/diagnostic until a human approves it here.

class ReviewDecision(BaseModel):
    status: str  # "approved" or "rejected"
    name: str | None = None          # optional edit before approving
    bloom_level: str | None = None   # optional edit before approving
    blueprint_weight: float | None = None


@router.get("/{course_id}/skills/proposed")
def list_proposed_skills(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Skills awaiting review for this course, with any 'possible duplicate'
    hint the proposer attached. Feeds the review UI (or read straight in
    Supabase for the demo)."""
    rows = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.proposed",
        "select": "id,name,bloom_level,blueprint_weight,proposed_source",
        "order": "name.asc",
    })
    return {"courseId": course_id, "proposed": rows}


@router.get("/{course_id}/skills/auto-matched")
def list_auto_matched_skills(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Skills that were auto-approved by cross-course match (they resembled a
    skill already approved in another course, above the AUTO_MATCH bar, so
    they went live without individual review, that's the scaling win).

    Surfacing them here is the auditability half of that trade: an instructor
    can SEE which of their live skills were inherited from elsewhere
    (canonical_skill_id is set, and proposed_source records what it matched),
    rather than the reuse being invisible. If an inherited skill's wording
    isn't quite right for THIS course, the detach endpoint below turns it
    back into a course-local proposed skill they can fine-tune."""
    rows = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",
        "canonical_skill_id": "not.is.null",
        "select": "id,name,bloom_level,blueprint_weight,module_ref,proposed_source,canonical_skill_id",
        "order": "name.asc",
    })
    return {"courseId": course_id, "autoMatched": rows}


@router.patch("/{course_id}/skills/{skill_id}/review")
def review_proposed_skill(
    course_id: str, skill_id: str, body: ReviewDecision,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Approve or reject a proposed skill, with optional inline edits. Only
    after approval does the skill feed the learner/instructor surfaces."""
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status must be approved or rejected")

    values: dict = {
        "status": body.status,
        "reviewed_by": user.user_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.status == "approved":
        if body.name is not None:
            values["name"] = body.name.strip()
        if body.bloom_level is not None:
            values["bloom_level"] = body.bloom_level
        if body.blueprint_weight is not None:
            values["blueprint_weight"] = max(0.5, min(2.0, float(body.blueprint_weight)))

    updated = db.update(
        "skills",
        {"id": f"eq.{skill_id}", "institution_id": f"eq.{user.institution_id}",
         "course_id": f"eq.{course_id}", "status": "eq.proposed"},
        values,
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "proposed skill not found")
    return {"skillId": skill_id, "status": body.status}


@router.patch("/{course_id}/skills/{skill_id}/detach")
def detach_auto_matched_skill(
    course_id: str, skill_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Turn an auto-matched skill back into a course-local skill for review.

    This is the reversibility half of cross-course auto-match: reuse is a
    default, not a lock-in. When an instructor decides an inherited skill's
    wording (or Bloom level, or weight) needs to be tuned specifically for
    THIS course, detaching clears canonical_skill_id and sends the row back
    to 'proposed', so it re-enters the normal review flow where they can edit
    it freely. It stops feeding the learner surfaces until re-approved (same
    as any proposed skill), which is the correct, conservative behavior, a
    skill mid-edit shouldn't be live.

    Only affects rows that were actually auto-matched (canonical_skill_id set
    and status approved); a 404 otherwise."""
    updated = db.update(
        "skills",
        {"id": f"eq.{skill_id}", "institution_id": f"eq.{user.institution_id}",
         "course_id": f"eq.{course_id}", "status": "eq.approved",
         "canonical_skill_id": "not.is.null"},
        {
            "status": "proposed",
            "canonical_skill_id": None,
            "proposed_source": "detached from cross-course match for course-specific tuning",
            "reviewed_by": None,
            "reviewed_at": None,
        },
    )
    if not updated:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "no auto-matched skill with that id in this course",
        )
    return {"skillId": skill_id, "status": "proposed", "detached": True}


# ---- Cohort reads (roster, stats, learner record) -------------------------
# The class overview needs more than one heatmap: who is in the class, how
# the cohort is moving, and where one learner actually is. These three are
# thin wrappers over app/twin/cohort.py, which owns the arithmetic.


@router.get("/{course_id}/roster")
def course_roster(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """One row per enrolled STUDENT, with real names.

    Two things worth stating because both were bugs:

    Students only. cohort.student_ids requires role='student' on BOTH the
    enrollment and the user, so a co-teacher or an admin who launched the
    course never lands in the roster as a learner with 0% mastery.

    Real names. The instructor is the teacher of record and already holds
    this roster in their gradebook; a class list of 'anon-8f2c1b' is not a
    privacy win, it is an unusable screen that gets worked around. The
    de-identification rule (CLAUDE.md 4) governs what leaves for a model or
    a researcher, and it still holds: every row carries its pseudonym, the
    UI can flip to pseudonyms for screen-sharing, and ai/prescriber.py is
    handed the pseudonym and never the name.
    """
    return cohort.roster(institution_id=user.institution_id, course_id=course_id)


@router.get("/{course_id}/stats")
def course_stats(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Cohort KPI strip plus the series behind every chart on the overview:
    readiness trend (from the worker's snapshots, real history), daily
    evidence volume, mastery band distribution, Bloom's coverage, per-skill
    breakdown weakest-first, and the human-in-the-loop decision counts."""
    return cohort.stats(institution_id=user.institution_id, course_id=course_id)


@router.get("/{course_id}/students/{user_id}/record")
def student_record(
    course_id: str, user_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """The teacher-facing read of one learner.

    Deliberately not the student's twin payload. The twin answers "how am I
    doing"; this answers "what does this learner need next, and what will I
    do about it" — so it adds identity, standing against the cohort,
    momentum (last 10 graded vs the 10 before), engagement pattern, and the
    readiness history the trend line is drawn from.
    """
    _assert_teaches_student(user=user, course_id=course_id, user_id=user_id)
    record = cohort.learner_record(
        institution_id=user.institution_id, course_id=course_id, user_id=user_id,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found in this course")
    return record


# ---- Prescriptive recommendations (the human-in-the-loop teaching gate) ---
# AI proposes next actions for one learner. NOTHING reaches the learner
# until an instructor approves or modifies it here. Same gate as the skill
# proposals above, different object: that one gates what Kala measures,
# this one gates what Kala asks a learner to do.


def _assert_teaches_student(*, user: CurrentUser, course_id: str, user_id: str) -> None:
    """The learner must be an enrolled student of THIS course. Without this
    an instructor could read or write a recommendation for any user id they
    could guess, since the API runs on the service role."""
    if user_id not in cohort.student_ids(
        institution_id=user.institution_id, course_id=course_id,
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found in this course")


REC_FIELDS = (
    "id,user_id,course_id,skill_id,title,action,kind,priority,rationale,evidence,"
    "status,confidence,expected_gain,source,decided_by,decided_at,decision_note,"
    "instructor_note,created_at,updated_at"
)


def _rec_out(row: dict, *, skill_names: dict[str, str] | None = None) -> dict:
    names = skill_names or {}
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "courseId": row["course_id"],
        "skillId": row.get("skill_id"),
        "skillName": names.get(row.get("skill_id") or "", None),
        "title": row.get("title") or row.get("action") or "Recommended next step",
        "kind": row.get("kind") or "practice",
        "priority": row.get("priority") or "medium",
        "rationale": row.get("rationale"),
        "evidence": row.get("evidence") or [],
        "status": row.get("status") or "suggested",
        "confidence": float(row["confidence"]) if row.get("confidence") is not None else None,
        "expectedGain": float(row["expected_gain"]) if row.get("expected_gain") is not None else None,
        "source": row.get("source"),
        "decidedBy": row.get("decided_by"),
        "decidedAt": row.get("decided_at"),
        "decisionNote": row.get("decision_note"),
        "instructorNote": row.get("instructor_note"),
        "createdAt": row.get("created_at"),
    }


def _skill_names(*, institution_id: str, course_id: str) -> dict[str, str]:
    rows = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "select": "id,name",
    })
    return {r["id"]: r["name"] for r in rows}


@router.get("/{course_id}/students/{user_id}/recommendations")
def list_recommendations(
    course_id: str, user_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Every recommendation for this learner, decided or not. Rejected rows
    stay in the list rather than disappearing: the decision history IS the
    human-in-the-loop record, and a teacher should be able to see they
    already turned something down."""
    _assert_teaches_student(user=user, course_id=course_id, user_id=user_id)
    rows = db.select("recommendations", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "user_id": f"eq.{user_id}", "select": REC_FIELDS, "order": "created_at.desc",
        "limit": "50",
    })
    names = _skill_names(institution_id=user.institution_id, course_id=course_id)
    return {
        "courseId": course_id,
        "userId": user_id,
        "recommendations": [_rec_out(r, skill_names=names) for r in rows],
    }


@router.post("/{course_id}/students/{user_id}/recommendations")
def generate_recommendations(
    course_id: str, user_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Ask Kala for next actions for this learner.

    De-identified before the call (the prescriber receives the pseudonym and
    numbers, never a name), persisted as status='suggested', and invisible
    to the learner until a teacher decides. Any pending suggestions from a
    previous run are superseded so the queue does not accumulate stale
    duplicates every time the teacher hits refresh — decided rows are never
    touched, because they are the audit trail.
    """
    _assert_teaches_student(user=user, course_id=course_id, user_id=user_id)
    record = cohort.learner_record(
        institution_id=user.institution_id, course_id=course_id, user_id=user_id,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found in this course")

    proposals, source = prescriber.recommend(
        pseudonym=record["pseudonym"], record=record,
    )
    if not proposals:
        return {"courseId": course_id, "userId": user_id, "generated": 0, "recommendations": []}

    # Supersede (not delete) the previous undecided batch: rejected as a
    # system action, so the audit trail shows the row existed and why it
    # went away.
    db.update(
        "recommendations",
        {"institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
         "user_id": f"eq.{user_id}", "status": "eq.suggested"},
        {"status": "rejected", "decision_note": "Superseded by a newer analysis",
         "decided_at": datetime.now(timezone.utc).isoformat(),
         "updated_at": datetime.now(timezone.utc).isoformat()},
    )

    rows = db.insert("recommendations", [{
        "institution_id": user.institution_id,
        "user_id": user_id,
        "course_id": course_id,
        "skill_id": p.get("skill_id"),
        "title": p["title"],
        "action": p["kind"],
        "kind": p["kind"],
        "priority": p["priority"],
        "rationale": p.get("rationale"),
        "evidence": p.get("evidence") or [],
        "confidence": p.get("confidence"),
        "expected_gain": p.get("expected_gain"),
        "source": source,
        "status": "suggested",
    } for p in proposals])

    names = _skill_names(institution_id=user.institution_id, course_id=course_id)
    return {
        "courseId": course_id,
        "userId": user_id,
        "generated": len(rows),
        "source": source,
        "recommendations": [_rec_out(r, skill_names=names) for r in rows],
    }


class RecommendationDecision(BaseModel):
    status: str                       # approved | modified | rejected
    title: str | None = None          # edit before approving
    kind: str | None = None
    priority: str | None = None
    decision_note: str | None = None  # why — the teacher's own words
    instructor_note: str | None = None  # shown to the learner alongside the action


@router.patch("/{course_id}/recommendations/{rec_id}")
def decide_recommendation(
    course_id: str, rec_id: str, body: RecommendationDecision,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Approve, modify, or reject one recommendation. This is the gate.

    'modified' is kept distinct from 'approved' rather than folded into it:
    "how often does a teacher edit the AI instead of taking it as written"
    is one of the study's actual research questions, and it is only
    answerable if the two decisions are different values in the column.
    """
    if body.status not in ("approved", "modified", "rejected"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "status must be approved, modified, or rejected",
        )

    values: dict = {
        "status": body.status,
        "decided_by": user.user_id,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.decision_note is not None:
        values["decision_note"] = body.decision_note.strip()[:1000]
    if body.instructor_note is not None:
        values["instructor_note"] = body.instructor_note.strip()[:1000]
    if body.status in ("approved", "modified"):
        if body.title:
            values["title"] = body.title.strip()[:120]
        if body.kind in ("practice", "lesson", "flashcards", "tutor", "diagnostic", "outreach"):
            values["kind"] = body.kind
            values["action"] = body.kind
        if body.priority in ("high", "medium", "low"):
            values["priority"] = body.priority

    updated = db.update(
        "recommendations",
        {"id": f"eq.{rec_id}", "institution_id": f"eq.{user.institution_id}",
         "course_id": f"eq.{course_id}"},
        values,
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation not found")

    names = _skill_names(institution_id=user.institution_id, course_id=course_id)
    return _rec_out(updated[0], skill_names=names)


class InterventionCreate(BaseModel):
    """A teacher writing their own action, not editing one Kala proposed."""
    title: str
    kind: str = "practice"
    priority: str = "medium"
    skill_id: str | None = None
    instructor_note: str | None = None


@router.post("/{course_id}/students/{user_id}/interventions")
def create_intervention(
    course_id: str, user_id: str, body: InterventionCreate,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """The teacher's own move. Lands in the learner's plan immediately with
    status='approved' and source='instructor' — a human wrote it, so there
    is nothing to gate. The symmetry matters: the same object carries both
    an AI proposal a teacher accepted and an action a teacher authored, so
    the learner's plan is one list and the audit trail shows which is
    which."""
    _assert_teaches_student(user=user, course_id=course_id, user_id=user_id)
    if body.kind not in ("practice", "lesson", "flashcards", "tutor", "diagnostic", "outreach"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown intervention kind")

    now = datetime.now(timezone.utc).isoformat()
    rows = db.insert("recommendations", [{
        "institution_id": user.institution_id,
        "user_id": user_id,
        "course_id": course_id,
        "skill_id": body.skill_id,
        "title": body.title.strip()[:120],
        "action": body.kind,
        "kind": body.kind,
        "priority": body.priority if body.priority in ("high", "medium", "low") else "medium",
        "rationale": "Assigned by the instructor.",
        "evidence": [],
        "source": "instructor",
        "status": "approved",
        "decided_by": user.user_id,
        "decided_at": now,
        "instructor_note": (body.instructor_note or "").strip()[:1000] or None,
        "updated_at": now,
    }])
    names = _skill_names(institution_id=user.institution_id, course_id=course_id)
    return _rec_out(rows[0], skill_names=names)
