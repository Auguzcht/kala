"""Cohort-level reads for the instructor surface.

Three shapes, one set of queries:

  roster(...)         one row per ENROLLED STUDENT with the numbers a
                      teacher scans a class by (readiness, accuracy, last
                      active, weakest skill, status).
  stats(...)          the cohort KPI strip + the series behind the charts.
  learner_record(...) the teacher-facing read of one learner. Deliberately
                      NOT the student's twin payload: same underlying
                      evidence, different question. The twin answers "how am
                      I doing"; the record answers "what does this learner
                      need next, and what will I do about it".

Naming posture, stated once because it is the thing people get wrong:
the instructor sees REAL NAMES here. They are the teacher of record; the
roster is already in their LMS gradebook. De-identification is a rule about
what leaves the system to a model or a researcher (CLAUDE.md rule 4), not a
rule that blinds a teacher to their own class. Every row still carries its
pseudonym so the UI can flip to de-identified mode for screen-sharing and
so nothing downstream has to look a name up. Model calls take `pseudonym`
and never `displayName` — see ai/prescriber.py.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from app.db import supabase as db
from app.twin import summary

# A learner counts as active if they produced evidence inside this window.
ACTIVE_WINDOW_DAYS = 7
# How far back the trend/engagement charts look.
TREND_WINDOW_DAYS = 28
BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


# ---- shared loaders -------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        parsed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _days_since(iso: str | None) -> int | None:
    parsed = _parse(iso)
    return None if parsed is None else max(0, (_now() - parsed).days)


def student_ids(*, institution_id: str, course_id: str) -> list[str]:
    """Enrolled students only.

    Two filters, not one, and that is the fix for "the roster shows people
    who aren't students". enrollments.role is what the LTI launch wrote for
    THIS course; users.role is what the person is in the institution. A
    co-teacher or an admin who launched the course once can end up with a
    student-ish enrollment row from a mis-mapped LTI role claim, and they
    should never appear in a class roster. Requiring both to say 'student'
    means a mis-mapped row on either side drops the person out rather than
    quietly listing an instructor as a learner with 0% mastery.
    """
    enrollments = db.select("enrollments", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "role": "eq.student", "select": "user_id", "order": "user_id.asc",
    })
    ids = [e["user_id"] for e in enrollments]
    if not ids:
        return []
    users = db.select("users", {
        "id": f"in.({','.join(ids)})", "institution_id": f"eq.{institution_id}",
        "role": "eq.student", "select": "id",
    })
    confirmed = {u["id"] for u in users}
    return [uid for uid in ids if uid in confirmed]


# Local dev / test LTI launchers (the IMS reference tool and similar) send
# a literal placeholder when you don't fill in the claims form by hand —
# most commonly exactly "GivenName" with no family name. That string then
# lands in user_profiles.display_name via the normal LTI upsert path, and
# nothing about it looks malformed to the code: it's a non-empty string,
# so it would otherwise render as a learner's actual name. Treating it as
# real produces a roster where several students are literally named
# "GivenName" — worse than the pseudonym fallback it was meant to replace.
_PLACEHOLDER_NAMES = {"givenname", "given name", "familyname", "family name", "test student"}


def load_identities(*, institution_id: str, user_ids: list[str]) -> dict[str, dict]:
    """{user_id: {displayName, pseudonym, initials}} for enrolled students.

    Shared with routers/dashboard.py's /at-risk endpoint, which is why this
    lost its underscore: two callers now need the same name -> identity
    resolution, and duplicating the query would risk the two surfaces
    drifting (one showing a name the other still shows a pseudonym for,
    which is exactly the bug this fixed).

    display_name lives in user_profiles (separated from users so erasure can
    drop it without touching the evidence log). If a profile row is missing
    or was purged, the pseudonym stands in — the roster degrades to
    de-identified rather than breaking.
    """
    if not user_ids:
        return {}
    users = db.select("users", {
        "id": f"in.({','.join(user_ids)})", "institution_id": f"eq.{institution_id}",
        "select": "id,pseudonym",
    })
    profiles = db.select("user_profiles", {
        "user_id": f"in.({','.join(user_ids)})", "select": "user_id,display_name",
    })
    names = {p["user_id"]: (p.get("display_name") or "").strip() for p in profiles}

    out: dict[str, dict] = {}
    for u in users:
        pseudonym = u.get("pseudonym") or "Student"
        raw_name = names.get(u["id"])
        # A single-word placeholder ("GivenName", "Test Student") is treated
        # the same as a missing name: fall back to the pseudonym rather than
        # display it as though it were the learner's actual name.
        display = raw_name if raw_name and raw_name.lower() not in _PLACEHOLDER_NAMES else pseudonym
        out[u["id"]] = {
            "userId": u["id"],
            "displayName": display,
            "pseudonym": pseudonym,
            "initials": "".join(p[0] for p in display.split()[:2]).upper() or "?",
        }
    return out


def _mastery(*, institution_id: str, course_id: str, user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []
    return db.select("mastery_state", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "user_id": f"in.({','.join(user_ids)})",
        "select": "user_id,skill_id,estimate,attempts,last_seen",
    })


def _evidence(*, institution_id: str, course_id: str, user_ids: list[str],
              limit: int = 2000) -> list[dict]:
    if not user_ids:
        return []
    return db.select("evidence_events", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "user_id": f"in.({','.join(user_ids)})",
        "select": "user_id,skill_id,type,correct,latency_ms,hints_used,created_at",
        "order": "created_at.desc", "limit": str(limit),
    })


def _approved_skills(*, institution_id: str, course_id: str) -> list[dict]:
    return db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level,blueprint_weight,module_ref", "order": "name.asc",
    })


# ---- roster ---------------------------------------------------------------

def _status_for(*, readiness: float | None, days_inactive: int | None,
                accuracy: float | None, attempts: int) -> str:
    """One word per learner, in the order a teacher would triage.

    'needs-support' is the only flag word and it is deliberately about the
    support they need, not a verdict on them (DESIGN.md). 'not-started' is
    kept separate from 'needs-support' because the intervention is
    different: one learner needs help with content, the other needs a nudge
    to begin.
    """
    if attempts == 0:
        return "not-started"
    if days_inactive is not None and days_inactive >= ACTIVE_WINDOW_DAYS:
        return "needs-support"
    if accuracy is not None and attempts >= 5 and accuracy < 0.4:
        return "needs-support"
    if readiness is not None and readiness >= 0.7:
        return "on-track"
    return "developing"


def roster(*, institution_id: str, course_id: str) -> dict:
    uids = student_ids(institution_id=institution_id, course_id=course_id)
    identities = load_identities(institution_id=institution_id, user_ids=uids)
    skills = _approved_skills(institution_id=institution_id, course_id=course_id)
    skill_names = {s["id"]: s["name"] for s in skills}
    mastery = _mastery(institution_id=institution_id, course_id=course_id, user_ids=uids)
    evidence = _evidence(institution_id=institution_id, course_id=course_id, user_ids=uids)

    by_user_mastery: dict[str, list[dict]] = {}
    for m in mastery:
        by_user_mastery.setdefault(m["user_id"], []).append(m)
    by_user_evidence: dict[str, list[dict]] = {}
    for e in evidence:
        by_user_evidence.setdefault(e["user_id"], []).append(e)

    rows = []
    for uid in uids:
        ident = identities.get(uid) or {
            "userId": uid, "displayName": "Student", "pseudonym": "Student", "initials": "?",
        }
        ms = by_user_mastery.get(uid, [])
        ev = by_user_evidence.get(uid, [])
        estimates = [float(m["estimate"]) for m in ms]
        readiness = round(sum(estimates) / len(estimates), 3) if estimates else None
        attempts = sum(int(m["attempts"]) for m in ms)
        graded = [e for e in ev if e.get("correct") is not None]
        accuracy = (
            round(sum(1 for e in graded if e["correct"]) / len(graded), 3) if graded else None
        )
        last_active = ev[0]["created_at"] if ev else None
        days_inactive = _days_since(last_active)

        # Weakest skill: never-attempted sorts weakest of all, matching the
        # server-side picker the learner's own "next up" uses, so the teacher
        # and the learner are looking at the same skill.
        weakest = None
        if skills:
            scored = [
                (float(next((m["estimate"] for m in ms if m["skill_id"] == s["id"]), -1.0)), s["id"])
                for s in skills
            ]
            scored.sort()
            weakest = skill_names.get(scored[0][1]) if scored else None

        rows.append({
            **ident,
            "readiness": readiness,
            "band": summary.band_for(readiness),
            "attempts": attempts,
            "evidenceCount": len(ev),
            "accuracy": accuracy,
            "lastActiveAt": last_active,
            "daysInactive": days_inactive,
            "weakestSkillName": weakest,
            "skillsWithEvidence": len(ms),
            "skillsTotal": len(skills),
            "status": _status_for(
                readiness=readiness, days_inactive=days_inactive,
                accuracy=accuracy, attempts=attempts,
            ),
        })

    # Triage order: who needs a teacher first, then who is furthest behind.
    rank = {"needs-support": 0, "not-started": 1, "developing": 2, "on-track": 3}
    rows.sort(key=lambda r: (rank.get(r["status"], 9), r["readiness"] if r["readiness"] is not None else -1))
    return {"courseId": course_id, "students": rows}


# ---- cohort stats ---------------------------------------------------------

def _daily_series(events: list[dict], *, days: int) -> list[dict]:
    """Evidence volume per day, correct vs missed, oldest -> newest, with
    empty days kept as zeros so the chart shows gaps instead of silently
    compressing a two-week break into a flat line."""
    start = (_now() - timedelta(days=days - 1)).date()
    buckets = {
        (start + timedelta(days=i)).isoformat(): {"correct": 0, "missed": 0, "ungraded": 0}
        for i in range(days)
    }
    for e in events:
        parsed = _parse(e.get("created_at"))
        if parsed is None:
            continue
        key = parsed.date().isoformat()
        if key not in buckets:
            continue
        if e.get("correct") is True:
            buckets[key]["correct"] += 1
        elif e.get("correct") is False:
            buckets[key]["missed"] += 1
        else:
            buckets[key]["ungraded"] += 1
    return [{"date": k, **v} for k, v in sorted(buckets.items())]


def stats(*, institution_id: str, course_id: str) -> dict:
    uids = student_ids(institution_id=institution_id, course_id=course_id)
    skills = _approved_skills(institution_id=institution_id, course_id=course_id)
    mastery = _mastery(institution_id=institution_id, course_id=course_id, user_ids=uids)
    evidence = _evidence(institution_id=institution_id, course_id=course_id, user_ids=uids)

    # --- per-learner rollups (readiness distribution, activity) ---
    by_user: dict[str, list[float]] = {}
    for m in mastery:
        by_user.setdefault(m["user_id"], []).append(float(m["estimate"]))
    readiness_by_user = {u: sum(v) / len(v) for u, v in by_user.items() if v}
    readiness_values = sorted(readiness_by_user.values())
    cohort_readiness = (
        round(sum(readiness_values) / len(readiness_values), 3) if readiness_values else None
    )
    median_readiness = (
        round(readiness_values[len(readiness_values) // 2], 3) if readiness_values else None
    )

    active_cutoff = _now() - timedelta(days=ACTIVE_WINDOW_DAYS)
    active_users = {
        e["user_id"] for e in evidence
        if (p := _parse(e.get("created_at"))) is not None and p >= active_cutoff
    }
    started_users = {e["user_id"] for e in evidence}

    graded = [e for e in evidence if e.get("correct") is not None]
    accuracy = round(sum(1 for e in graded if e["correct"]) / len(graded), 3) if graded else None
    latencies = [int(e["latency_ms"]) for e in evidence if e.get("latency_ms")]
    median_latency = sorted(latencies)[len(latencies) // 2] if latencies else None
    hints = sum(int(e.get("hints_used") or 0) for e in evidence)

    # --- band distribution across every (learner, skill) cell ---
    cells = Counter()
    covered = {(m["user_id"], m["skill_id"]) for m in mastery}
    for m in mastery:
        cells[summary.band_for(float(m["estimate"]))] += 1
    cells["no-evidence"] += max(0, len(uids) * len(skills) - len(covered))
    band_distribution = [
        {"band": b, "count": cells.get(b, 0)}
        for b in ("no-evidence", "developing", "proficient", "mastered")
    ]

    # --- Bloom's coverage: cohort mastery per rung of the ladder ---
    est_by_skill: dict[str, list[float]] = {}
    for m in mastery:
        est_by_skill.setdefault(m["skill_id"], []).append(float(m["estimate"]))
    bloom_rows = []
    for level in BLOOM_ORDER:
        level_skills = [s for s in skills if (s.get("bloom_level") or "").lower() == level]
        if not level_skills:
            continue
        vals = [e for s in level_skills for e in est_by_skill.get(s["id"], [])]
        bloom_rows.append({
            "level": level,
            "skills": len(level_skills),
            "estimate": round(sum(vals) / len(vals), 3) if vals else None,
        })

    # --- per-skill cohort estimate, weakest first: the teacher's reteach list ---
    skill_rows = sorted(
        (
            {
                "skillId": s["id"],
                "name": s["name"],
                "bloomLevel": s.get("bloom_level"),
                "moduleRef": s.get("module_ref"),
                "estimate": (
                    round(sum(est_by_skill[s["id"]]) / len(est_by_skill[s["id"]]), 3)
                    if est_by_skill.get(s["id"]) else None
                ),
                "learnersWithEvidence": len(est_by_skill.get(s["id"], [])),
                "band": summary.band_for(
                    sum(est_by_skill[s["id"]]) / len(est_by_skill[s["id"]])
                    if est_by_skill.get(s["id"]) else None
                ),
            }
            for s in skills
        ),
        key=lambda r: (r["estimate"] is None, r["estimate"] if r["estimate"] is not None else 0),
    )
    # Sort note: measured skills come first, weakest to strongest, and
    # never-measured skills fall to the END rather than the front. They
    # would technically rank "weakest" at 0%, but a reteach list whose top
    # six entries are all "no evidence yet" tells a teacher nothing about
    # what to reteach — that is a coverage problem, and the KPI strip
    # already reports it as skillsCovered/skillsTracked.

    # --- readiness trend from the worker's snapshots (real history, not a
    # curve fitted on the client) ---
    since = (_now() - timedelta(days=TREND_WINDOW_DAYS)).isoformat()
    snapshots = db.select("readiness_snapshots", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "created_at": f"gte.{since}",
        "select": "user_id,score,created_at", "order": "created_at.asc", "limit": "5000",
    })
    trend_buckets: dict[str, list[float]] = {}
    for s in snapshots:
        parsed = _parse(s.get("created_at"))
        if parsed is None:
            continue
        trend_buckets.setdefault(parsed.date().isoformat(), []).append(float(s["score"]))
    readiness_trend = [
        {"date": d, "readiness": round(sum(v) / len(v), 3), "learners": len(v)}
        for d, v in sorted(trend_buckets.items())
    ]

    # --- teacher decision counts: the human-in-the-loop scoreboard ---
    decisions = db.select("recommendations", {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "select": "status", "limit": "1000",
    })
    decision_counts = Counter(d.get("status") or "suggested" for d in decisions)

    return {
        "courseId": course_id,
        "learners": len(uids),
        "activeLearners": len(active_users),
        "startedLearners": len(started_users),
        "notStartedLearners": max(0, len(uids) - len(started_users)),
        "cohortReadiness": cohort_readiness,
        "medianReadiness": median_readiness,
        "accuracy": accuracy,
        "evidenceCount": len(evidence),
        "medianLatencyMs": median_latency,
        "hintsUsed": hints,
        "skillsTracked": len(skills),
        "skillsCovered": len({m["skill_id"] for m in mastery}),
        "bandDistribution": band_distribution,
        "bloomCoverage": bloom_rows,
        "skillBreakdown": skill_rows,
        "readinessTrend": readiness_trend,
        "activitySeries": _daily_series(evidence, days=14),
        "decisions": {
            "pending": decision_counts.get("suggested", 0),
            "approved": decision_counts.get("approved", 0) + decision_counts.get("modified", 0),
            "rejected": decision_counts.get("rejected", 0),
            "completed": decision_counts.get("completed", 0),
        },
    }


# ---- one learner, from the teacher's side ---------------------------------

def learner_record(*, institution_id: str, course_id: str, user_id: str) -> dict | None:
    """The teacher's read of one learner.

    Shares the mastery/evidence spine with the student's twin but answers a
    different question, so the shape is different on purpose: it adds the
    identity block, the momentum comparison against the cohort, the
    engagement pattern, and the per-skill delta that tells a teacher WHERE
    to intervene rather than just how the learner is doing.
    """
    identities = load_identities(institution_id=institution_id, user_ids=[user_id])
    ident = identities.get(user_id)
    if ident is None:
        return None

    skills = _approved_skills(institution_id=institution_id, course_id=course_id)
    mastery = _mastery(institution_id=institution_id, course_id=course_id, user_ids=[user_id])
    est = {m["skill_id"]: m for m in mastery}

    events = db.select("evidence_events", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{institution_id}",
        "select": "id,skill_id,type,correct,latency_ms,hints_used,created_at",
        "order": "created_at.desc", "limit": "200",
    })
    skill_names = {s["id"]: s["name"] for s in skills}

    skill_rows = [{
        "skillId": s["id"],
        "name": s["name"],
        "bloomLevel": s.get("bloom_level"),
        "moduleRef": s.get("module_ref"),
        "estimate": float(est[s["id"]]["estimate"]) if s["id"] in est else None,
        "attempts": int(est[s["id"]]["attempts"]) if s["id"] in est else 0,
        "lastSeen": est[s["id"]].get("last_seen") if s["id"] in est else None,
        "band": summary.band_for(float(est[s["id"]]["estimate"]) if s["id"] in est else None),
    } for s in skills]

    estimates = [r["estimate"] for r in skill_rows if r["estimate"] is not None]
    readiness = round(sum(estimates) / len(estimates), 3) if estimates else None

    # Cohort comparison: the single most useful number a teacher can have
    # about one learner is where they sit relative to everyone else, and it
    # costs one extra query.
    peers = student_ids(institution_id=institution_id, course_id=course_id)
    peer_mastery = _mastery(institution_id=institution_id, course_id=course_id, user_ids=peers)
    peer_by_user: dict[str, list[float]] = {}
    for m in peer_mastery:
        peer_by_user.setdefault(m["user_id"], []).append(float(m["estimate"]))
    peer_readiness = sorted(sum(v) / len(v) for v in peer_by_user.values() if v)
    cohort_readiness = (
        round(sum(peer_readiness) / len(peer_readiness), 3) if peer_readiness else None
    )
    percentile = None
    if readiness is not None and len(peer_readiness) > 1:
        below = sum(1 for r in peer_readiness if r < readiness)
        percentile = round(100 * below / (len(peer_readiness) - 1))

    graded = [e for e in events if e.get("correct") is not None]
    accuracy = round(sum(1 for e in graded if e["correct"]) / len(graded), 3) if graded else None
    # Momentum: last 10 graded vs the 10 before. A learner at 45% who is
    # climbing needs a different conversation than one at 45% who is
    # sliding, and a static mastery number hides that entirely.
    recent, prior = graded[:10], graded[10:20]
    recent_rate = (sum(1 for e in recent if e["correct"]) / len(recent)) if recent else None
    prior_rate = (sum(1 for e in prior if e["correct"]) / len(prior)) if prior else None
    momentum = (
        round(recent_rate - prior_rate, 3)
        if recent_rate is not None and prior_rate is not None else None
    )

    by_type = Counter(e["type"] for e in events)
    last_active = events[0]["created_at"] if events else None

    snapshots = db.select("readiness_snapshots", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{institution_id}",
        "select": "score,created_at", "order": "created_at.asc", "limit": "60",
    })

    return {
        "courseId": course_id,
        **ident,
        "readiness": readiness,
        "band": summary.band_for(readiness),
        "cohortReadiness": cohort_readiness,
        "percentile": percentile,
        "accuracy": accuracy,
        "momentum": momentum,
        "attempts": sum(r["attempts"] for r in skill_rows),
        "evidenceCount": len(events),
        "hintsUsed": sum(int(e.get("hints_used") or 0) for e in events),
        "lastActiveAt": last_active,
        "daysInactive": _days_since(last_active),
        "status": _status_for(
            readiness=readiness, days_inactive=_days_since(last_active),
            accuracy=accuracy, attempts=sum(r["attempts"] for r in skill_rows),
        ),
        "skills": skill_rows,
        "activityByType": [{"type": t, "count": c} for t, c in by_type.most_common()],
        "activitySeries": _daily_series(events, days=14),
        "readinessTrend": [
            {"date": (_parse(s["created_at"]) or _now()).date().isoformat(),
             "readiness": round(float(s["score"]), 3)}
            for s in snapshots
        ],
        "evidence": [{
            "id": e["id"],
            "type": e["type"],
            "correct": e.get("correct"),
            "latencyMs": e.get("latency_ms"),
            "skillName": skill_names.get(e.get("skill_id"), "Unknown skill"),
            "createdAt": e.get("created_at"),
        } for e in events[:25]],
    }
