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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai.concurrency import map_concurrent
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, require_valid_course_id
from app.learn import items as item_gen
from app.learn import srs, xp

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


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
        )}

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
            "select": "id,skill_id,prompt,choices",
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

    # 2) Top up with new cards for skills that have no scheduled card yet.
    if len(cards) < limit:
        tracked = db.select("srs_state", {
            "user_id": f"eq.{user.user_id}", "course_id": f"eq.{course_id}",
            "select": "skill_id",
        })
        tracked_skill_ids = {t["skill_id"] for t in tracked}
        fresh_skills = [s for sid, s in skills.items() if sid not in tracked_skill_ids]

        # Generation is one Bedrock call per skill, independent of the
        # others — parallelized so seeding N new cards is one round trip's
        # worth of wall-clock time, not N serial ones. Scheduling writes
        # (ensure_tracked) stay sequential after, they're cheap DB I/O and
        # keeping them in order avoids any need to reason about interleaving.
        to_generate = fresh_skills[: limit - len(cards)]
        generated = map_concurrent(
            lambda skill: item_gen.generate_question(
                institution_id=user.institution_id, course_id=course_id,
                skill=skill, kind="flashcard",
            ),
            to_generate,
        )
        for skill, card in zip(to_generate, generated):
            srs.ensure_tracked(
                institution_id=user.institution_id, user_id=user.user_id,
                course_id=course_id, item_id=card["id"], skill_id=skill["id"],
                module_ref=skill.get("module_ref"),
            )
            cards.append({
                "itemId": card["id"],
                "skillId": skill["id"],
                "skillName": skill.get("name"),
                "prompt": card["prompt"],
                "state": "new",
                "box": 0,
            })

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
            "select": "id,correct_choice_id,explanation,choices",
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

    return {
        "courseId": course_id,
        "cards": cards,
        "stats": srs.stats(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=skill_id,
        ),
    }


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
        "select": "id,skill_id", "limit": "1",
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

    return {
        "remembered": body.remembered,
        "graduated": sched.graduated,
        "dueInHours": round(sched.interval_hours, 1),
        "box": sched.box,
        "reward": xp.summary(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }

