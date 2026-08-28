"""XP, streaks, and badges — DERIVED from the append-only evidence log, never
a parallel currency.

The masterplan is explicit (section 10.1): rewards must be tied to the twin so
they mean something. XP is earned for evidence that moves mastery, streaks for
spaced consistent practice, badges per skill and per Bloom level. Keeping all
of it as a pure function of evidence_events (+ the derived mastery_state) means:

  * it cannot be gamed from the client — there is no writable XP balance, the
    number is recomputed from immutable evidence on read;
  * it is always consistent with the twin — the same events that move mastery
    are the ones that grant XP;
  * it is fully recomputable and auditable — a research export can reproduce
    every number from the same log.

This module does no writes. It reads evidence_events and mastery_state and
computes the reward view.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.db import supabase as db

# XP weights. Correct evidence is the mastery-moving signal, so it carries the
# reward; a small participation grant keeps a hard session from feeling empty
# without rewarding raw activity over learning.
_XP_CORRECT = 10
_XP_ATTEMPT = 2

# Mastery thresholds for badges (match the qualitative bands the twin already
# shows; kept here as the single source so they can be tuned centrally).
_PROFICIENT = 0.7
_MASTERED = 0.85


def _parse_ts(value: str) -> datetime:
    # PostgREST returns ISO-8601; tolerate a trailing Z.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _streak_days(created_ats: list[str]) -> int:
    """Consecutive calendar days (UTC) up to today with at least one evidence
    event. Rewards spacing/consistency, not volume."""
    if not created_ats:
        return 0
    days = {_parse_ts(c).astimezone(timezone.utc).date() for c in created_ats}
    streak = 0
    cursor = datetime.now(timezone.utc).date()
    # Allow the streak to count from today OR yesterday (so an unfinished
    # today doesn't zero a real streak before the user studies).
    if cursor not in days:
        cursor = date.fromordinal(cursor.toordinal() - 1)
        if cursor not in days:
            return 0
    while cursor in days:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return streak


def summary(*, institution_id: str, user_id: str, course_id: str) -> dict:
    """The reward view for one student in one course: total XP, current streak,
    and earned badges. All derived, no writes."""
    events = db.select("evidence_events", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "correct,created_at",
    })
    attempts = len(events)
    correct = sum(1 for e in events if e.get("correct") is True)
    xp = correct * _XP_CORRECT + attempts * _XP_ATTEMPT
    streak = _streak_days([e["created_at"] for e in events if e.get("created_at")])

    badges = _badges(institution_id=institution_id, user_id=user_id, course_id=course_id)

    return {
        "xp": xp,
        "attempts": attempts,
        "correct": correct,
        "streakDays": streak,
        "badges": badges,
    }


def _badges(*, institution_id: str, user_id: str, course_id: str) -> list[dict]:
    """Skill-mastery and Bloom-level badges, read off mastery_state + skills.
    A skill badge is earned at the proficient band; a Bloom badge when every
    approved skill at that Bloom level is at least proficient."""
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved", "select": "id,name,bloom_level",
    })
    if not skills:
        return []
    mastery = db.select("mastery_state", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate",
    })
    est = {m["skill_id"]: float(m["estimate"]) for m in mastery}

    badges: list[dict] = []
    for s in skills:
        e = est.get(s["id"])
        if e is None:
            continue
        if e >= _MASTERED:
            badges.append({"kind": "skill", "label": s["name"], "tier": "mastered"})
        elif e >= _PROFICIENT:
            badges.append({"kind": "skill", "label": s["name"], "tier": "proficient"})

    # Bloom badges: all skills at a level proficient-or-better.
    by_bloom: dict[str, list[str]] = {}
    for s in skills:
        if s.get("bloom_level"):
            by_bloom.setdefault(s["bloom_level"], []).append(s["id"])
    for bloom, ids in by_bloom.items():
        if ids and all(est.get(i, 0.0) >= _PROFICIENT for i in ids):
            badges.append({"kind": "bloom", "label": bloom, "tier": "proficient"})

    return badges
