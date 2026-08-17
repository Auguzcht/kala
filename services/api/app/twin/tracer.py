"""Mastery tracer. September uses a simple, defensible update (Elo-style with
recency); BKT vs Elo is tracked in the masterplan open-decisions log. The tracer
runs server-side only; the client submits raw evidence, never mastery."""
from __future__ import annotations

from app.db import supabase as db

_K = 0.15  # learning-rate style step


def apply_evidence(*, institution_id: str, user_id: str, course_id: str,
                   skill_id: str, correct: bool) -> dict:
    rows = db.select("mastery_state", {
        "user_id": f"eq.{user_id}", "skill_id": f"eq.{skill_id}",
        "select": "estimate,attempts", "limit": "1",
    })
    prior = float(rows[0]["estimate"]) if rows else 0.5
    attempts = int(rows[0]["attempts"]) if rows else 0
    target = 1.0 if correct else 0.0
    estimate = max(0.0, min(1.0, prior + _K * (target - prior)))
    saved = db.upsert("mastery_state", [{
        "institution_id": institution_id, "user_id": user_id,
        "course_id": course_id, "skill_id": skill_id,
        "estimate": estimate, "attempts": attempts + 1, "last_seen": "now()",
    }], on_conflict="user_id,skill_id")
    return saved[0] if saved else {"estimate": estimate}
