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
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

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
KNOWN_INTERVAL_HOURS = 21 * 24

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


def next_state(current_state: CardState, *, outcome: str, mode: str,
               was_due: bool, reviewed_at: datetime | None = None) -> ScheduleResult:
    """Scheduler boundary used by transactional review writers.

    The database RPC performs the same transition while holding the schedule
    row lock. Early successes are logged by the caller but leave this state
    unchanged; misses always lapse.
    """
    if outcome not in ("again", "good"):
        raise ValueError("outcome must be 'again' or 'good'")
    if mode not in ("flashcard", "quiz"):
        raise ValueError("mode must be 'flashcard' or 'quiz'")
    if outcome == "good" and not was_due:
        return ScheduleResult(
            box=current_state.box, ease_milli=current_state.ease_milli,
            streak=current_state.streak, reps=current_state.reps,
            lapses=current_state.lapses,
            interval_hours=interval_hours(box=current_state.box, ease_milli=current_state.ease_milli),
            graduated=is_mastered(box=current_state.box, streak=current_state.streak),
        )
    return schedule_after(current_state, correct=outcome == "good")


def is_mastered(*, box: int, streak: int) -> bool:
    """Row-level graduation predicate, matching schedule_after's rule. Used by
    read queries to exclude mastered cards from normal review without encoding
    the threshold into SQL."""
    return box >= _MAX_BOX and streak >= GRADUATE_STREAK


def is_due(row: dict | None, *, at: datetime, inclusive: bool = True) -> bool:
    """Whether a studied, ungraduated card is due by the supplied horizon.

    Membership uses an exclusive local-midnight horizon for dueToday; review
    uses an inclusive current-time horizon. Untracked and never-studied cards
    belong to the new-card pool, even if tracking gave them a past due_at.
    """
    if not row or int(row.get("reps", 0)) == 0 or not row.get("due_at"):
        return False
    if is_mastered(box=int(row["box"]), streak=int(row["streak"])):
        return False
    due_at = datetime.fromisoformat(row["due_at"].replace("Z", "+00:00"))
    return due_at <= at if inclusive else due_at < at


def interval_hours(*, box: int, ease_milli: int) -> float:
    """Current scheduled interval from the stored scheduler parameters."""
    return _BOX_BASE_HOURS[box] * (ease_milli / 1000.0)


def card_state(*, reps: int, last_outcome: str | None, lapses: int,
               box: int, ease_milli: int) -> str:
    """Derive the student-facing memory state without storing a second state."""
    if reps == 0:
        return "new"
    if last_outcome == "again":
        return "slipping" if reps > lapses else "learning"
    if last_outcome == "good" and interval_hours(box=box, ease_milli=ease_milli) >= KNOWN_INTERVAL_HOURS:
        return "known"
    return "learning"


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


def new_remaining_today(*, institution_id: str, user_id: str, course_id: str,
                        daily_cap: int = 20) -> int:
    """Count only first claims that spent the institution-local daily allowance."""
    institutions = db.select("institutions", {
        "id": f"eq.{institution_id}", "select": "timezone", "limit": "1",
    })
    zone = ZoneInfo(institutions[0].get("timezone") or "UTC") if institutions else ZoneInfo("UTC")
    now = datetime.now(timezone.utc)
    local_date = now.astimezone(zone).date()
    day_start = datetime.combine(local_date, time.min, zone).astimezone(timezone.utc)
    day_end = datetime.combine(local_date + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    rows = db.select("srs_state", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}", "daily_new_claimed": "eq.true",
        "and": f"(created_at.gte.{day_start.isoformat()},created_at.lt.{day_end.isoformat()})",
        "select": "item_id", "limit": "1000",
    })
    return max(0, daily_cap - len(rows))


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
        "last_outcome": "good" if correct else "again",
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
    often and graduated cards stop surfacing in normal review.

    Returns the srs_state rows joined to their generated_items (client-safe
    fields only — never the answer key). Empty list is a valid, common state
    (nothing due yet), which the caller turns into "you're all caught up".
    """
    now = _now()
    params: dict[str, str] = {
        "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}",
        "due_at": f"lte.{now.isoformat()}",
        "select": "item_id,skill_id,box,ease_milli,streak,reps,lapses,last_outcome,due_at",
        "order": "due_at.asc",
        "limit": str(max(1, limit) * 3),  # over-fetch, then drop mastered below
    }
    if module_ref is not None:
        params["module_ref"] = f"eq.{module_ref}"
    if skill_id is not None:
        params["skill_id"] = f"eq.{skill_id}"
    rows = db.select("srs_state", params)
    active_ids = _active_item_ids(institution_id=institution_id, course_id=course_id, rows=rows)
    rows = [r for r in rows if r["item_id"] in active_ids]

    fresh = [r for r in rows if is_due(r, at=now)]
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
        "select": "item_id,box,streak,due_at",
    }
    if skill_id is not None:
        params["skill_id"] = f"eq.{skill_id}"
    rows = db.select("srs_state", params)
    active_ids = _active_item_ids(institution_id=institution_id, course_id=course_id, rows=rows)
    rows = [r for r in rows if r["item_id"] in active_ids]
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


def _active_item_ids(*, institution_id: str, course_id: str, rows: list[dict]) -> set[str]:
    """Retired or rejected-skill SRS rows are historical scheduling state,
    not live cards. Resolve them through the canonical active-item filter."""
    item_ids = list(dict.fromkeys(r["item_id"] for r in rows if r.get("item_id")))
    if not item_ids:
        return set()
    active = db.select("generated_items", {
        "id": f"in.({','.join(item_ids)})", "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}", "retired_at": "is.null",
        "skills.status": "eq.approved",
        "select": "id,skills!inner(status)",
    })
    return {item["id"] for item in active}
