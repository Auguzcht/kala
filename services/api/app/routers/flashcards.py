"""Flashcard endpoints — STUDY MODE.

A flashcard is a flip: front shows the prompt, you tap, the back reveals the
answer and explanation, and you mark it yourself ("Got it" / "Review again").
This is memorization, not assessment, so there is no server grading here and
no multiple-choice UI. The same generated item can still be taken as a graded
quiz (test mode) through /practice/{course_id}/set — that is the bridge from
studying to a mastery signal.

Two consequences of the split, both deliberate:

  1. Gating and slicing still happen here. A card you mark "Review again"
     reschedules to box 0 and resurfaces sooner; a card recalled several times
     running graduates out of normal review. Scheduling is srs_state, and
     srs.review already takes a plain `correct: bool` — self-mark is passed
     straight through, so the schedule logic is unchanged.

  2. Self-mark does NOT feed the twin. review() writes an evidence_event
     (type 'flashcard') so study behavior still reaches the research export,
     but never calls tracer.apply_evidence, so mastery_state stays put.
     Mastery is fed by diagnostic, quiz (test mode), and tutor checks. A
     student who wants a mastery signal from what they studied takes the
     test on the far side of the bridge.

Hint and Explain are plain /tutor/ask calls with grounded content; they
inform, they do not grade, and they do not touch the schedule.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from app.bank.serving import bank_enabled, pick_bank_items, record_exposure
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, require_valid_course_id
from app.learn import items as item_gen
from app.learn import srs, xp

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/{course_id}/skills/{skill_id}/cards")
def skill_cards(
    course_id: str = Depends(require_valid_course_id),
    skill_id: str = Path(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Read the complete live card membership for one approved skill.

    This is a browse list, not a session selector. It never creates schedule,
    exposure, review, or mastery rows.
    """
    skills = db.select("skills", {
        "id": f"eq.{skill_id}", "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}", "status": "eq.approved",
        "select": "id", "limit": "1",
    })
    if not skills:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found")

    items = db.select("generated_items", {
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}",
        "retired_at": "is.null",
        "or": "(and(kind.eq.practice,origin.eq.bank),kind.eq.flashcard)",
        "skills.status": "eq.approved",
        "select": "id,kind,prompt,front,back,choices,correct_choice_id,explanation,created_at,skills!inner(status)",
        "order": "created_at.asc", "limit": "1000",
    })
    item_ids = [item["id"] for item in items]
    schedules = db.select("srs_state", {
        "institution_id": f"eq.{user.institution_id}", "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}",
        "select": "item_id,box,ease_milli,streak,reps,lapses,due_at,last_outcome",
    }) if item_ids else []
    by_item = {row["item_id"]: row for row in schedules if row["item_id"] in set(item_ids)}

    institution = db.select("institutions", {
        "id": f"eq.{user.institution_id}", "select": "timezone", "limit": "1",
    })
    zone = ZoneInfo(institution[0].get("timezone") or "UTC") if institution else ZoneInfo("UTC")
    now = datetime.now(timezone.utc)
    local_tomorrow = datetime.combine(now.astimezone(zone).date() + timedelta(days=1), time.min, zone)
    day_end_utc = local_tomorrow.astimezone(timezone.utc)

    counts = {state: 0 for state in ("new", "learning", "slipping", "known")}
    due_today = 0
    cards = []
    for item in items:
        row = by_item.get(item["id"])
        state = "new" if row is None else srs.card_state(
            reps=int(row["reps"]), last_outcome=row.get("last_outcome"),
            lapses=int(row["lapses"]), box=int(row["box"]),
            ease_milli=int(row["ease_milli"]),
        )
        counts[state] += 1
        due_at = row.get("due_at") if row else None
        due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00")) if due_at else None
        due = due_dt is not None and due_dt <= now
        if due_dt is not None and due_dt < day_end_utc:
            due_today += 1
        label = item.get("back") if item["kind"] == "flashcard" else item_gen.correct_label(item)
        cards.append({
            "itemId": item["id"], "prompt": item.get("front") or item["prompt"],
            "back": {"label": label, "explanation": item.get("explanation") or ""},
            "state": state, "due": due, "dueAt": due_at,
        })
    return {"skillId": skill_id, "counts": {**counts, "dueToday": due_today}, "cards": cards}


def _skill_map(*, institution_id: str, course_id: str,
               module_ref: str | None, skill_id: str | None = None) -> dict[str, dict]:
    params = {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved", "select": "id,name,bloom_level,module_ref",
    }
    if module_ref is not None:
        params["module_ref"] = f"eq.{module_ref}"
    if skill_id is not None:
        params["id"] = f"eq.{skill_id}"
    return {s["id"]: s for s in db.select("skills", params)}


@router.get("/{course_id}/deck")
def deck(
    course_id: str = Depends(require_valid_course_id),
    limit: int = 10,
    module_ref: str | None = None,
    skill_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    """The review queue: due scheduled cards first, topped up with fresh cards
    for skills the student hasn't started. Answer keys never leave the server.
    `skill_id` is the topic picker's explicit override — when set, the whole
    deck (due cards AND fresh top-up) scopes to that one skill instead of the
    course-wide due-first mix, same "auto vs chosen" pattern as practice.
    """
    if skill_id is not None:
        # Same validation practice.py does for its own explicit skill_id —
        # this is client input, not server-derived, so an id from another
        # course or an unapproved skill should 404, not silently render as
        # "nothing due" for a topic that was never real to begin with.
        exists = db.select("skills", {
            "id": f"eq.{skill_id}", "course_id": f"eq.{course_id}",
            "institution_id": f"eq.{user.institution_id}", "status": "eq.approved",
            "select": "id", "limit": "1",
        })
        if not exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "skill not found")

    skills = _skill_map(
        institution_id=user.institution_id, course_id=course_id,
        module_ref=module_ref, skill_id=skill_id,
    )
    if not skills:
        return {"courseId": course_id, "cards": [], "stats": srs.stats(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=skill_id,
        ), "bankStatus": {"status": "no_material", "mcqReady": 0}}
    course_rows = db.select("courses", {
        "id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}",
        "select": "id,bank_serving", "limit": "1",
    })
    use_bank = bool(course_rows and bank_enabled(course_rows[0], "study"))

    # 1) Due, already-scheduled cards (most overdue first, mastered excluded).
    due = srs.due_cards(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, limit=limit, module_ref=module_ref, skill_id=skill_id,
    )
    due_item_ids = [d["item_id"] for d in due]
    items_by_id: dict[str, dict] = {}
    if due_item_ids:
        rows = db.select("generated_items", {
            "id": f"in.({','.join(due_item_ids)})",
            "institution_id": f"eq.{user.institution_id}",
            "course_id": f"eq.{course_id}", "retired_at": "is.null",
            "kind": "in.(practice,flashcard)",
            "skills.status": "eq.approved",
            "select": "id,skill_id,prompt,choices,origin,skills!inner(status)",
        })
        items_by_id = {r["id"]: r for r in rows}

    cards: list[dict] = []
    for d in due:
        it = items_by_id.get(d["item_id"])
        if not it or not it.get("choices"):
            continue
        skill = skills.get(d["skill_id"], {})
        cards.append({
            "itemId": it["id"],
            "skillId": d["skill_id"],
            "skillName": skill.get("name"),
            "prompt": it["prompt"],
            "state": "due",
            "box": d["box"],
        })

    # 2) Top up from the bank when enabled. Courses without bank serving may
    # continue to serve already-scheduled due cards above, but never generate
    # new cards from a student request.
    if use_bank and len(cards) < limit:
        bank_items = pick_bank_items(
            user.user_id, course_id, skill_id, limit - len(cards), "study",
            institution_id=user.institution_id,
        )
        for item in bank_items:
            skill = skills.get(item["skill_id"], {})
            srs.ensure_tracked(
                institution_id=user.institution_id, user_id=user.user_id,
                course_id=course_id, item_id=item["id"], skill_id=item["skill_id"],
                module_ref=skill.get("module_ref"),
            )
            record_exposure(
                institution_id=user.institution_id, user_id=user.user_id,
                course_id=course_id, skill_id=item["skill_id"], item_id=item["id"], studied=True,
            )
            cards.append({"itemId": item["id"], "skillId": item["skill_id"],
                          "skillName": skill.get("name"), "prompt": item["prompt"],
                          "state": "new", "box": 0})

    # 3) Derive the study back (answer label + explanation) for every card in
    # ONE query. Study mode shows a flip, so it needs the answer the MCQ
    # hides — but only as a plain label, and only through this endpoint (the
    # quiz surface never receives a back; it grades server-side). Deriving it
    # here rather than widening generate_question's return keeps the answer
    # out of every other caller's payload: diagnostic appends the generator's
    # dict straight into its response, so an answer field on that return would
    # have leaked.
    item_ids = [c["itemId"] for c in cards]
    if item_ids:
        back_rows = db.select("generated_items", {
            "id": f"in.({','.join(item_ids)})",
            "institution_id": f"eq.{user.institution_id}",
            "course_id": f"eq.{course_id}", "retired_at": "is.null",
            "skills.status": "eq.approved",
            "select": "id,correct_choice_id,explanation,choices,skills!inner(status)",
        })
        backs = {
            r["id"]: {
                "label": item_gen.correct_label(r),
                "explanation": r.get("explanation") or "",
            }
            for r in back_rows
        }
        for card in cards:
            card["back"] = backs.get(card["itemId"], {"label": None, "explanation": ""})

    result = {
        "courseId": course_id,
        "cards": cards,
        "stats": srs.stats(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=skill_id,
        ),
    }
    if skill_id is not None and use_bank:
        state = db.select("skill_bank_state", {
            "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}",
            "select": "status,mcq_ready,mcq_target", "limit": "1",
        })
        if state:
            row = state[0]
            result["bankStatus"] = {
                "status": row.get("status"), "mcqReady": row.get("mcq_ready", 0),
            }
    elif not use_bank:
        result["bankStatus"] = {"status": "no_material", "mcqReady": 0}
    return result


class ReviewBody(BaseModel):
    item_id: str
    remembered: bool
    latency_ms: int = 0


@router.post("/{course_id}/review")
def review(
    body: ReviewBody,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Self-mark one study card and advance its spaced-repetition schedule.

    Study mode is memorization, not assessment: the student flips the card,
    sees the answer, and marks "Got it" or "Review again" themselves. There is
    no server grading here — `remembered` is the student's own call, by design.

    What that means for the twin: this writes an evidence_event (type
    'flashcard', correct=remembered) but does NOT call tracer.apply_evidence,
    so mastery_state never moves on self-report. That row is still written on
    purpose — the research export (0003_research.sql) aggregates flashcard
    evidence into research_evidence_anon / research_cohort_daily, and dropping
    it would make every self-paced study session invisible to that pipeline.
    Mastery is fed by diagnostic, quiz (test mode), and tutor checks only; the
    study -> test bridge is what routes studying into a real mastery signal.
    XP still moves off study because xp.summary reads evidence_events, which is
    the intended behavior (reward the work, don't inflate mastery).
    """
    rows = db.select("generated_items", {
        "id": f"eq.{body.item_id}", "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}", "retired_at": "is.null",
        "skills.status": "eq.approved",
        "select": "id,skill_id,skills!inner(status)", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    skill_id = rows[0].get("skill_id")

    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": skill_id, "type": "flashcard",
        "correct": body.remembered, "latency_ms": body.latency_ms,
        "hints_used": 0,
    }])
    # Deliberately NO tracer.apply_evidence here — see the docstring. Self-mark
    # is not assessment; mastery moves on graded evidence only.
    sched = srs.review(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, item_id=body.item_id, skill_id=skill_id,
        correct=body.remembered,
    )
    record_exposure(
        institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        skill_id=skill_id, item_id=body.item_id, answered=True, correct=body.remembered,
    )

    return {
        "remembered": body.remembered,
        "graduated": sched.graduated,
        "dueInHours": round(sched.interval_hours, 1),
        "box": sched.box,
        "reward": xp.summary(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }
