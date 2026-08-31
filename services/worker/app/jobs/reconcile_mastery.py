"""Twin reconciliation: replay evidence_events and rebuild mastery_state.

mastery_state is documented (packages/db/migrations/0001_init.sql) as
"Derived state (recomputable from evidence)". Before this job, nothing
actually recomputed it — the only writer was the live request path
(app/twin/tracer.py, applied once per answer as it happens). If a request
ever wrote an evidence_events row but failed before or during the tracer
update (a timeout, a crashed Lambda, a bug), mastery_state would silently
diverge from the log and nothing would ever notice or fix it.

This job makes "recomputable from evidence" true rather than aspirational:
for every (user, skill) pair with any evidence, replay every event in
created_at order through the exact same update rule tracer.py uses, and
upsert the result. Idempotent and safe to run on a schedule — a
(user, skill) with unchanged evidence replays to the same estimate every
time.

The update rule (order matters, so this MUST mirror app/twin/tracer.py's
apply_evidence exactly): estimate starts at 0.5, and each event nudges it
toward 1.0 (correct) or 0.0 (incorrect) by a fixed learning-rate step _K.
"""
from __future__ import annotations

from app.config import get_settings
from app.db import supabase as db


def _replay(events: list[dict], *, k: float) -> float:
    """Same math as tracer.apply_evidence, applied to a full history instead
    of one event, in created_at order (ascending — the query already sorts
    this way)."""
    estimate = 0.5
    for e in events:
        target = 1.0 if e["correct"] else 0.0
        estimate = max(0.0, min(1.0, estimate + k * (target - estimate)))
    return estimate


def run(*, institution_id: str | None = None) -> dict:
    """Reconcile mastery_state for one institution, or every institution if
    institution_id is None (the normal scheduled path). Returns counts for
    the worker's summary log."""
    s = get_settings()
    institutions = (
        [{"id": institution_id}] if institution_id
        else db.select("institutions", {"select": "id"})
    )

    pairs_checked = 0
    pairs_corrected = 0

    for inst in institutions:
        inst_id = inst["id"]
        events = db.select("evidence_events", {
            "institution_id": f"eq.{inst_id}",
            "select": "user_id,course_id,skill_id,correct,created_at",
            "order": "created_at.asc",
            "limit": "50000",  # generous ceiling for a pilot-scale cohort; see note below
        })
        # Group by (user_id, skill_id). skill_id is nullable on evidence_events
        # in principle (see 0001_init.sql), but a null skill can't roll up to
        # any mastery_state row, so those events are excluded, same as the
        # live tracer path (which is always called with a concrete skill_id).
        by_pair: dict[tuple[str, str], list[dict]] = {}
        course_of: dict[tuple[str, str], str] = {}
        for e in events:
            if not e.get("skill_id"):
                continue
            key = (e["user_id"], e["skill_id"])
            by_pair.setdefault(key, []).append(e)
            course_of[key] = e["course_id"]

        if not by_pair:
            continue

        existing = db.select("mastery_state", {
            "institution_id": f"eq.{inst_id}",
            "select": "user_id,skill_id,estimate,attempts",
        })
        existing_by_pair = {(r["user_id"], r["skill_id"]): r for r in existing}

        rows_to_upsert = []
        for (user_id, skill_id), evs in by_pair.items():
            pairs_checked += 1
            recomputed = round(_replay(evs, k=s.tracer_k), 6)
            current = existing_by_pair.get((user_id, skill_id))
            current_estimate = round(float(current["estimate"]), 6) if current else None
            attempts = len(evs)
            if current_estimate is not None and current_estimate == recomputed and current["attempts"] == attempts:
                continue  # already consistent with the log, nothing to write
            pairs_corrected += 1
            rows_to_upsert.append({
                "institution_id": inst_id,
                "user_id": user_id,
                "course_id": course_of[(user_id, skill_id)],
                "skill_id": skill_id,
                "estimate": recomputed,
                "attempts": attempts,
                "last_seen": evs[-1]["created_at"],
            })

        if rows_to_upsert:
            db.upsert("mastery_state", rows_to_upsert, on_conflict="user_id,skill_id")

    return {"pairsChecked": pairs_checked, "pairsCorrected": pairs_corrected}
