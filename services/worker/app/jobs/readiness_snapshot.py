"""Readiness snapshots: turn the twin's current-state readiness number into
a real time series.

readiness_snapshots (packages/db/migrations/0001_init.sql) has existed
since the first migration and nothing has ever written to it.
app/twin/readiness.py computes a live readiness score on every request
(GET /courses/{id}/twin) but only returns it, never persists it. That means
Kala's "longitudinal digital learning twin" claim has no actual longitude
for readiness — only mastery_state's updated_at timestamps hint at when
things changed, and there's no queryable "was this student on track two
weeks ago" answer.

This job closes that gap the same way ingest already treats content: one
snapshot per (student, course) per scheduled run, using the exact formula
app/twin/readiness.py uses (mean of that student's mastery_state estimates
in the course), so a future "readiness over time" chart on the student or
instructor side has real rows to read the moment it's built. No API
endpoint reads this table yet — writing the history now means whenever
that chart gets built, the backlog isn't empty.

Only students with at least one mastery_state row get a snapshot — a
student with zero evidence has no readiness signal yet, and a
0.0-vs-no-row distinction matters (see readiness.py's own early return),
so this job preserves it rather than writing a misleading 0.
"""
from __future__ import annotations

from app.db import supabase as db


def run(*, institution_id: str | None = None) -> dict:
    filters = {
        "role": "eq.student",
        "select": "user_id,course_id,institution_id",
    }
    if institution_id:
        filters["institution_id"] = f"eq.{institution_id}"
    enrollments = db.select("enrollments", filters)

    if not enrollments:
        return {"snapshots": 0}

    course_ids = list({e["course_id"] for e in enrollments})
    mastery = db.select("mastery_state", {
        "course_id": f"in.({','.join(course_ids)})",
        "select": "user_id,course_id,estimate",
    })
    by_pair: dict[tuple[str, str], list[float]] = {}
    for m in mastery:
        by_pair.setdefault((m["user_id"], m["course_id"]), []).append(float(m["estimate"]))

    rows = []
    for e in enrollments:
        key = (e["user_id"], e["course_id"])
        estimates = by_pair.get(key)
        if not estimates:
            continue  # no evidence yet — no snapshot, not a misleading 0.0
        score = round(sum(estimates) / len(estimates), 3)
        rows.append({
            "institution_id": e["institution_id"],
            "user_id": e["user_id"],
            "course_id": e["course_id"],
            "score": score,
        })

    if rows:
        # Plain insert: readiness_snapshots is an append-only time series by
        # design (one row per run, not upserted), so history accumulates
        # rather than being overwritten.
        db.insert("readiness_snapshots", rows)

    return {"snapshots": len(rows)}
