"""Spaced-repetition scheduler for the learn loop.

Why per CARD, not per skill
---------------------------
Scheduling state lives per (user, generated_item), and skill mastery is the
rollup of a skill's cards into the existing mastery_state (owned by the
tracer). This is the higher-headroom choice, deliberately:

  * A per-card schedule yields a per-item forgetting curve — the exact
    signal (which specific fact this student keeps lapsing on, and how fast)
    that a per-skill schedule would average away and could never recover
    later. That item-level history is the research dataset described in the
    masterplan; throwing it away at write time is irreversible.
  * Skill mastery is still available for free: it is a rollup over the card
    schedules / evidence for that skill, computed on read. So we keep the
    fine grain AND the coarse grain, rather than collapsing to the coarse one.
  * It matches how the reference apps (Anki, SM-2, Gizmo) actually behave —
    each card graduates on its own clock.

The mechanics (Leitner box + SM-2 ease)
---------------------------------------
Each card sits in a Leitner box 0..5. The box sets the base interval; an
SM-2-style ease factor (stored x1000 as an int to avoid float drift in the
DB) stretches or compresses it. A correct recall promotes the box and nudges
ease up; a lapse drops the card back to box 0, halves nothing but lowers ease,
and increments the lapse counter so the forgetting curve is queryable.

A card is considered MASTERED (stops surfacing in normal review) once it has
reached the top box with a streak at/above GRADUATE_STREAK. That threshold is
data-driven on the row (box + streak), not hardcoded into a query, so it can
be tuned centrally without a migration.

This module is pure scheduling math (`schedule_after`) plus a thin persistence
layer (`review`, `due_cards`, `ensure_tracked`). The math half has no I/O so
it is unit-tested directly, which is where the risk lives.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.db import supabase as db

# Base interval per Leitner box, in hours, BEFORE the ease multiplier.
# box 0 is intentionally sub-day so a just-lapsed / brand-new card comes back
# in the same session-ish window; the tail grows toward long-term retention.
_BOX_BASE_HOURS: dict[int, float] = {
    0: 4.0,      # ~same day
    1: 24.0,     # 1 day
    2: 72.0,     # 3 days
    3: 168.0,    # 1 week
    4: 384.0,    # ~16 days
    5: 840.0,    # ~35 days
}
_MAX_BOX = 5

_EASE_MIN = 1300
_EASE_MAX = 3000
_EASE_UP = 60      # correct recall nudges ease up a touch
_EASE_DOWN = 200   # a lapse costs more than a success gains (net-conservative)

# A card is "mastered" (drops out of normal review) at the top box once it has
# been recalled this many times in a row. Kept here as the single source of
# truth for the threshold; the DB stores the raw box/streak so this can move.
GRADUATE_STREAK = 3


@dataclass(frozen=True)
class CardState:
    """The scheduling-relevant fields of an srs_state row. Plain data so the
    scheduling math can be exercised with no database."""
    box: int
    ease_milli: int
    streak: int
    reps: int
    lapses: int


@dataclass(frozen=True)
class ScheduleResult:
    box: int
    ease_milli: int
    streak: int
    reps: int
    lapses: int
    interval_hours: float
    graduated: bool


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def schedule_after(state: CardState, *, correct: bool) -> ScheduleResult:
    """Pure transition: given a card's current state and whether the student
    just recalled it, return the next state and the interval until it is due.
    No I/O — this is the piece that is unit-tested.
    """
    reps = state.reps + 1

    if correct:
        box = min(state.box + 1, _MAX_BOX)
        ease_milli = _clamp(state.ease_milli + _EASE_UP, _EASE_MIN, _EASE_MAX)
        streak = state.streak + 1
        lapses = state.lapses
    else:
        # Lapse: back to the most-frequent box, ease penalised, streak reset,
        # lapse recorded (this is what makes a missed card show up more often
        # AND feeds the forgetting-curve dataset).
        box = 0
        ease_milli = _clamp(state.ease_milli - _EASE_DOWN, _EASE_MIN, _EASE_MAX)
        streak = 0
        lapses = state.lapses + 1

    interval_hours = _BOX_BASE_HOURS[box] * (ease_milli / 1000.0)
    graduated = box >= _MAX_BOX and streak >= GRADUATE_STREAK

    return ScheduleResult(
        box=box, ease_milli=ease_milli, streak=streak, reps=reps,
        lapses=lapses, interval_hours=interval_hours, graduated=graduated,
    )


def is_mastered(*, box: int, streak: int) -> bool:
    """Row-level graduation predicate, matching schedule_after's rule. Used by
    read queries to exclude mastered cards from normal review without encoding
    the threshold into SQL."""
    return box >= _MAX_BOX and streak >= GRADUATE_STREAK


# ---- persistence ----------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_tracked(*, institution_id: str, user_id: str, course_id: str,
                   item_id: str, skill_id: str | None,
                   module_ref: str | None = None) -> None:
    """Create a schedule row for a card the first time it is shown, due now.
    Idempotent by construction: we SELECT first and only INSERT when absent,
    so an existing card's box/streak is never clobbered back to defaults (a
    plain upsert would merge-overwrite them — that would silently reset
    progress every time the card was re-shown). Best-effort: a schedule write
    must never block delivering the card, and review() is the authoritative
    writer regardless."""
    try:
        existing = db.select("srs_state", {
            "user_id": f"eq.{user_id}", "item_id": f"eq.{item_id}",
            "select": "item_id", "limit": "1",
        })
        if existing:
            return
        db.insert("srs_state", [{
            "institution_id": institution_id,
            "user_id": user_id,
            "course_id": course_id,
            "item_id": item_id,
            "skill_id": skill_id,
            "module_ref": module_ref,
            "due_at": _now().isoformat(),
        }], prefer="return=minimal")
    except Exception:
        # Losing a tracking row just means the card is created on first review
        # instead of first show; harmless. Never surface to the student.
        pass


def review(*, institution_id: str, user_id: str, course_id: str,
           item_id: str, skill_id: str | None, correct: bool) -> ScheduleResult:
    """Advance a card's schedule after a review. Reads the current row (or
    starts from a fresh CardState if none), applies the pure transition, and
    persists the next due time. Returns the ScheduleResult so callers can
    surface graduation / award XP off a mastery-moving event."""
    rows = db.select("srs_state", {
        "user_id": f"eq.{user_id}", "item_id": f"eq.{item_id}",
        "select": "box,ease_milli,streak,reps,lapses", "limit": "1",
    })
    if rows:
        r = rows[0]
        current = CardState(
            box=int(r["box"]), ease_milli=int(r["ease_milli"]),
            streak=int(r["streak"]), reps=int(r["reps"]), lapses=int(r["lapses"]),
        )
    else:
        current = CardState(box=0, ease_milli=2500, streak=0, reps=0, lapses=0)

    result = schedule_after(current, correct=correct)
    due_at = _now() + timedelta(hours=result.interval_hours)

    db.upsert("srs_state", [{
        "institution_id": institution_id,
        "user_id": user_id,
        "course_id": course_id,
        "item_id": item_id,
        "skill_id": skill_id,
        "box": result.box,
        "ease_milli": result.ease_milli,
        "streak": result.streak,
        "reps": result.reps,
        "lapses": result.lapses,
        "due_at": due_at.isoformat(),
        "last_reviewed_at": _now().isoformat(),
    }], on_conflict="user_id,item_id")

    return result


def due_cards(*, institution_id: str, user_id: str, course_id: str,
              limit: int = 20, module_ref: str | None = None,
              skill_id: str | None = None) -> list[dict]:
    """The cards this student should see now, most-overdue first, excluding
    mastered ones. This replaces the old flat top-N skill slice: selection is
    driven by the schedule (due date + box), so missed cards resurface more
    often and mastered cards drop out until their long interval elapses.

    Returns the srs_state rows joined to their generated_items (client-safe
    fields only — never the answer key). Empty list is a valid, common state
    (nothing due yet), which the caller turns into "you're all caught up".
    """
    params: dict[str, str] = {
        "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}",
        "due_at": f"lte.{_now().isoformat()}",
        "select": "item_id,skill_id,box,streak,due_at",
        "order": "due_at.asc",
        "limit": str(max(1, limit) * 3),  # over-fetch, then drop mastered below
    }
    if module_ref is not None:
        params["module_ref"] = f"eq.{module_ref}"
    if skill_id is not None:
        params["skill_id"] = f"eq.{skill_id}"
    rows = db.select("srs_state", params)

    fresh = [r for r in rows if not is_mastered(box=int(r["box"]), streak=int(r["streak"]))]
    return fresh[:limit]


def stats(*, institution_id: str, user_id: str, course_id: str,
          skill_id: str | None = None) -> dict:
    """Lightweight review-queue summary for the course home surface: how many
    cards are due, learning (box 0-2), young, and mastered. This is the
    'show the one number that drives the next action' metadata — computed from
    the schedule the student already has, no extra model calls. `skill_id`
    scopes this to one topic — without it, a topic-scoped deck of 2 cards
    would sit under a stats block still reporting the whole course's due
    count, which contradicts what's actually on screen."""
    params = {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "box,streak,due_at",
    }
    if skill_id is not None:
        params["skill_id"] = f"eq.{skill_id}"
    rows = db.select("srs_state", params)
    now_iso = _now().isoformat()
    due = sum(1 for r in rows if r["due_at"] <= now_iso
              and not is_mastered(box=int(r["box"]), streak=int(r["streak"])))
    mastered = sum(1 for r in rows if is_mastered(box=int(r["box"]), streak=int(r["streak"])))
    learning = sum(1 for r in rows if int(r["box"]) <= 2
                   and not is_mastered(box=int(r["box"]), streak=int(r["streak"])))
    return {
        "tracked": len(rows),
        "due": due,
        "learning": learning,
        "mastered": mastered,
    }
