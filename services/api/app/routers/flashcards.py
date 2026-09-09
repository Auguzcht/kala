"""Flashcard endpoints, spaced-repetition edition.

This is the active-recall surface from the target design (prompt first, then
options, with Hint / Reveal / Explain). Two things changed from the first cut:

  1. Selection is scheduled, not a flat top-N. The deck is driven by
     srs_state: cards that are DUE come back first, and a card you missed
     resurfaces sooner and more often (box 0) until you recall it several
     times running, at which point it graduates out of normal review. New
     skills with no card yet get one generated to seed the schedule.

  2. Cards are graded server-side. A flashcard is a real MCQ generated_item
     with its answer key kept on the server (same pattern as practice), so
     "knew it" is not a self-report the client could fake — the student picks
     an option and the server decides correctness, feeds the tracer, writes a
     flashcard evidence_event, and advances the schedule.

Three actions on a card, three different contracts:
  - Hint  is NOT this router — it's a grounded /tutor/ask call before the
    student answers, counted client-side into hints_used and sent along with
    whichever of review/reveal ends the card.
  - Reveal is /reveal below: a pre-commit Show Answer. Because the server
    never lets a client see an answer key for free, revealing forces an
    immediate lapse (correct=False, schedule drops to the most-frequent box)
    BEFORE the answer is returned — there is no free peek, same as any real
    spaced-repetition tool.
  - Explain is a post-answer /tutor/ask call with style=detail on the
    grounded content, same mechanism as Hint, different timing.

Review returns the reward view (XP/streak) so the gamified header has real,
twin-grounded numbers to show.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai.concurrency import map_concurrent
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user
from app.learn import items as item_gen
from app.learn import srs, xp
from app.twin import tracer

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
def deck(course_id: str, limit: int = 10, module_ref: str | None = None,
         skill_id: str | None = None,
         user: CurrentUser = Depends(get_current_user)):
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
            "choices": it["choices"],
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
                "choices": card["choices"],
                "state": "new",
                "box": 0,
            })

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
    choice_id: str
    latency_ms: int = 0
    hints_used: int = 0


@router.post("/{course_id}/review")
def review(course_id: str, body: ReviewBody, user: CurrentUser = Depends(get_current_user)):
    """Grade one recall attempt server-side, write evidence, move the tracer,
    and advance the spaced-repetition schedule. Returns the graded result plus
    the schedule outcome and the twin-grounded reward view."""
    try:
        graded = item_gen.grade(
            institution_id=user.institution_id, item_id=body.item_id, choice_id=body.choice_id,
        )
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")

    skill_id = graded["skillId"]
    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": skill_id, "type": "flashcard",
        "correct": graded["correct"], "latency_ms": body.latency_ms,
        "hints_used": body.hints_used,
    }])
    state = tracer.apply_evidence(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id, correct=graded["correct"],
    )
    sched = srs.review(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, item_id=body.item_id, skill_id=skill_id,
        correct=graded["correct"],
    )

    return {
        "correct": graded["correct"],
        "explanation": graded["explanation"],
        "graduated": sched.graduated,
        "dueInHours": round(sched.interval_hours, 1),
        "box": sched.box,
        "mastery": state.get("estimate"),
        "reward": xp.summary(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }


class RevealBody(BaseModel):
    item_id: str
    latency_ms: int = 0


@router.post("/{course_id}/reveal")
def reveal(course_id: str, body: RevealBody, user: CurrentUser = Depends(get_current_user)):
    """Pre-commit Show Answer, matching the target design's separate Reveal
    action (distinct from picking a choice). Seeing the answer without
    recalling it is treated as a lapse and committed BEFORE the answer is
    returned, exactly like a real spaced-repetition tool: there is no free
    peek. Evidence is written with correct=False and the SRS schedule drops
    the card back to its most-frequent box, so a revealed card resurfaces
    sooner, same as a missed one.

    Client contract: once a card has been revealed, treat it as terminal —
    do NOT also call POST /review for that item_id afterward. This endpoint
    already recorded the lapse; a follow-up review call would double-write
    evidence and could let a correct guess after the reveal quietly overwrite
    the lapse it just cost. The deck's next card comes from GET /deck as
    normal; there is no "undo" on a reveal, again matching a real SRS tool.
    """
    try:
        revealed = item_gen.reveal(
            institution_id=user.institution_id, item_id=body.item_id,
        )
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")

    skill_id = revealed["skillId"]
    db.insert_evidence([{
        "institution_id": user.institution_id, "user_id": user.user_id,
        "course_id": course_id, "skill_id": skill_id, "type": "flashcard",
        "correct": False, "latency_ms": body.latency_ms, "hints_used": 0,
    }])
    state = tracer.apply_evidence(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, skill_id=skill_id, correct=False,
    )
    sched = srs.review(
        institution_id=user.institution_id, user_id=user.user_id,
        course_id=course_id, item_id=body.item_id, skill_id=skill_id,
        correct=False,
    )

    return {
        "revealed": True,
        "correctChoiceId": revealed["correctChoiceId"],
        "correctLabel": revealed["correctLabel"],
        "explanation": revealed["explanation"],
        "dueInHours": round(sched.interval_hours, 1),
        "box": sched.box,
        "mastery": state.get("estimate"),
        "reward": xp.summary(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
        ),
    }
