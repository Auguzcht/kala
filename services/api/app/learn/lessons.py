"""Guided lessons: persistent, generated-once, comprehension-gated
walkthroughs (the Gizmo "step-by-step" surface).

Lifecycle (on demand, generate once, then replay) — matches how the
reference app behaves: the first time a student opens a skill's lesson, the
AI builds it and it is stored; every open after that replays the stored
lesson, no regeneration.

  Phase 1 — outline: one reasoning-tier call reads the skill's grounded
  course context and proposes an ordered set of teach-steps (title + focus +
  Bloom level). This is "AI creates the topics".

  Phase 2 — per-step content: for each step, one call produces structured
  teaching content (summary, detail bullets, a common misconception, a key
  takeaway) AND a comprehension-check MCQ. This is "AI goes through each
  topic to create the content to be discussed", and it is what makes the
  guided tutor a MASTERY SOURCE: the check is a real generated_items row
  (kind='tutor') graded server-side, so passing it writes a tutor
  evidence_event and moves the twin, exactly like practice does.

Everything is grounded in real course content via RAG (Kala's source of
truth is the LMS, so the student never uploads anything). Generation is
best-effort with deterministic fallbacks, mirroring the rest of the learn
loop: a model hiccup degrades a step to a plain explanation rather than
failing the whole lesson.

Idempotency: (course_id, skill_id) is unique on guided_lessons. get_or_
generate_lesson returns the stored lesson if one exists; only the first
caller pays the generation cost.
"""
from __future__ import annotations

import json

import httpx

from app.ai import bedrock, rag
from app.ai.concurrency import map_concurrent
from app.ai.router import get_model_for
from app.db import supabase as db
from app.learn import items as item_gen

_OUTLINE_SYSTEM = (
    "You are Kala, planning a short guided lesson for ONE skill, grounded "
    "ONLY in the supplied course excerpt. Break the skill into an ordered "
    "sequence of 3-6 teach-steps that build from recall toward application "
    "(read -> understand -> apply). Return strict JSON and nothing else: "
    '{"steps": [{"title": str, "focus": str, "bloom_level": str}]}. '
    "bloom_level is one of remember, understand, apply, analyze, evaluate, "
    "create. Do not invent facts beyond the excerpt."
)

_STEP_SYSTEM = (
    "You are Kala, teaching ONE step of a lesson, grounded ONLY in the "
    "supplied course excerpt. Explain the step's focus to a learner without "
    "assuming prior knowledge, then surface one common misconception and a "
    "one-line key takeaway. Return strict JSON and nothing else: "
    '{"summary": str, "detail_points": [str, ...], "misconception": str, '
    '"key_takeaway": str}. Keep detail_points to 2-4 short bullets. Do not '
    "invent facts beyond the excerpt."
)

_MAX_STEPS = 6
_VALID_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def _context_for(*, institution_id: str, course_id: str, skill: dict) -> tuple[str, list[str]]:
    """Grounded context for a skill plus the chunk ids used, so the lesson can
    record provenance (which passages it was built from)."""
    chunks = rag.retrieve(
        institution_id=institution_id, course_id=course_id, query=skill["name"], k=4,
    )
    if not chunks:
        return skill["name"], []
    text = "\n---\n".join(c.get("chunk_text", "") for c in chunks)
    chunk_ids = [c["id"] for c in chunks if c.get("id")]
    return text, chunk_ids


def _generate_outline(*, skill: dict, context: str) -> list[dict]:
    """Phase 1. Returns a validated list of step specs. Falls back to a single
    step named after the skill if generation fails, so a lesson always has at
    least one step."""
    try:
        raw = bedrock.converse(
            model_id=get_model_for("reasoning"),
            system=_OUTLINE_SYSTEM,
            messages=[{"role": "user", "content": [{"text": json.dumps({
                "skill": skill["name"], "bloom_level": skill.get("bloom_level"),
                "excerpt": context,
            })}]}],
            max_tokens=768,
        )
        parsed = _parse_json(raw)
        steps = parsed.get("steps", [])
        clean: list[dict] = []
        for s in steps[:_MAX_STEPS]:
            title = (s.get("title") or "").strip()
            if not title:
                continue
            bloom = s.get("bloom_level")
            clean.append({
                "title": title,
                "focus": (s.get("focus") or title).strip(),
                "bloom_level": bloom if bloom in _VALID_BLOOM else skill.get("bloom_level"),
            })
        if clean:
            return clean
    except Exception:
        pass
    # Fallback: one step, so the lesson is never empty.
    return [{
        "title": skill["name"],
        "focus": skill["name"],
        "bloom_level": skill.get("bloom_level"),
    }]


def _generate_step_content(*, skill: dict, step: dict, context: str) -> dict:
    """Phase 2a. Structured teaching content for one step. Deterministic
    fallback keeps the step renderable if generation fails."""
    try:
        raw = bedrock.converse(
            model_id=get_model_for("default"),
            system=_STEP_SYSTEM,
            messages=[{"role": "user", "content": [{"text": json.dumps({
                "skill": skill["name"], "step_title": step["title"],
                "step_focus": step["focus"], "excerpt": context,
            })}]}],
            max_tokens=640,
        )
        parsed = _parse_json(raw)
        details = parsed.get("detail_points", [])
        if not isinstance(details, list):
            details = []
        return {
            "summary": (parsed.get("summary") or step["focus"]).strip(),
            "detail_points": [str(d) for d in details][:4],
            "misconception": (parsed.get("misconception") or "").strip() or None,
            "key_takeaway": (parsed.get("key_takeaway") or "").strip() or None,
        }
    except Exception:
        return {
            "summary": step["focus"],
            "detail_points": [],
            "misconception": None,
            "key_takeaway": None,
        }


def get_or_generate_lesson(*, institution_id: str, course_id: str, skill: dict) -> dict:
    """Return the stored guided lesson for this skill, generating and
    persisting it on first request. Idempotent via the (course_id, skill_id)
    unique constraint.

    Three states a lookup can find, each handled explicitly (this replaces an
    earlier version that only handled 'ready' and could get permanently
    stuck):

      ready       -> load and return, no generation.
      generating  -> another request created the shell (or a prior attempt
                     crashed mid-loop and never reached 'ready'/'failed'; at
                     this system's scale — one demo cohort, not high
                     concurrency — there is no separate worker to distinguish
                     "still running" from "abandoned", so the safe choice is
                     to reclaim and (re)generate rather than serve a lesson
                     that may never arrive). Any leftover steps from a
                     partial attempt are cleared first so positions never
                     collide.
      failed      -> a previous attempt threw; same reclaim-and-retry path.
      not found   -> insert a fresh shell. If a concurrent request already
                     did this between our SELECT and INSERT, PostgREST
                     returns 409 (unique_violation on course_id, skill_id);
                     that is caught and treated as "found", not an error.

    Generation itself is wrapped so any exception marks the row 'failed'
    (never left at 'generating') before re-raising, so the NEXT open can
    always recover instead of 500ing forever.

    Performance note on the 'ready' fast path: this used to re-select
    guided_lessons a second time inside load_lesson() even though the row
    was just fetched right here to check its status — a fully redundant
    round trip on the hot path (a student re-opening a lesson they've
    already generated should be near-instant, not pay for an extra DB call
    every time). The existence check below now selects every field the
    assembly step needs, so the ready case calls _assemble_lesson() directly
    with the row already in hand instead of going through load_lesson()'s
    own select.
    """
    lesson_fields = "id,status,skill_id,module_ref,title"
    existing = db.select("guided_lessons", {
        "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill['id']}",
        "institution_id": f"eq.{institution_id}",
        "select": lesson_fields, "limit": "1",
    })

    if existing:
        row = existing[0]
        if row["status"] == "ready":
            return _assemble_lesson(lesson_row=row, institution_id=institution_id)
        lesson_id = row["id"]
        _reclaim_for_regeneration(lesson_id)
    else:
        try:
            lesson_rows = db.insert("guided_lessons", [_lesson_shell(
                institution_id=institution_id, course_id=course_id, skill=skill,
            )])
            lesson_id = lesson_rows[0]["id"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                # Lost the race to a concurrent first-open. Re-select and
                # reclaim rather than fail — this IS the "found" case now.
                refetched = db.select("guided_lessons", {
                    "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill['id']}",
                    "institution_id": f"eq.{institution_id}",
                    "select": lesson_fields, "limit": "1",
                })
                if not refetched:
                    raise  # genuinely unexpected; surface the original error
                if refetched[0]["status"] == "ready":
                    return _assemble_lesson(lesson_row=refetched[0], institution_id=institution_id)
                lesson_id = refetched[0]["id"]
                _reclaim_for_regeneration(lesson_id)
            else:
                raise

    try:
        _generate_steps_into(
            institution_id=institution_id, course_id=course_id,
            skill=skill, lesson_id=lesson_id,
        )
    except Exception:
        # Never leave the row stuck at 'generating' — the next open must be
        # able to retry instead of hitting a permanent dead end.
        db.update("guided_lessons", {"id": f"eq.{lesson_id}"}, {"status": "failed"})
        raise

    db.update("guided_lessons", {"id": f"eq.{lesson_id}"}, {"status": "ready"})
    return load_lesson(institution_id=institution_id, lesson_id=lesson_id)


def _lesson_shell(*, institution_id: str, course_id: str, skill: dict) -> dict:
    _, chunk_ids = _context_for(
        institution_id=institution_id, course_id=course_id, skill=skill,
    )
    # Context itself is re-derived by _generate_steps_into rather than
    # threaded through — RAG retrieval is cheap and idempotent, and keeping
    # the shell insert independent of a value only needed later keeps this
    # function (and the whole insert-then-generate split) trivially retry-safe.
    return {
        "institution_id": institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "module_ref": skill.get("module_ref"),
        "title": skill["name"],
        "status": "generating",
        "source_chunk_ids": chunk_ids or None,
    }


def _reclaim_for_regeneration(lesson_id: str) -> None:
    """Clear any steps left by a partial/crashed attempt and mark the lesson
    'generating' again before retrying. Deleting first means step `position`
    can never collide with leftovers from the earlier attempt."""
    db.delete("guided_lesson_steps", {"lesson_id": f"eq.{lesson_id}"})
    db.update("guided_lessons", {"id": f"eq.{lesson_id}"}, {"status": "generating"})


def _build_step_payload(*, institution_id: str, course_id: str, skill: dict,
                        step: dict, context: str) -> dict:
    """One step's worth of work: teaching content + its comprehension check.
    Fully independent of every other step (only reads the shared, read-only
    `context`), which is what makes running these on a thread pool safe."""
    content = _generate_step_content(skill=skill, step=step, context=context)

    # The comprehension check: a real generated_items MCQ (kind='tutor'),
    # so passing it grades server-side and writes a tutor evidence_event.
    # Reuses the tested item generator rather than a parallel path.
    check_item_id = None
    try:
        check = item_gen.generate_question(
            institution_id=institution_id, course_id=course_id,
            skill=skill, kind="tutor",
        )
        check_item_id = check["id"]
    except Exception:
        check_item_id = None  # explanation-only step; still valid

    return {"content": content, "check_item_id": check_item_id, "bloom_level": step.get("bloom_level")}


def _generate_steps_into(*, institution_id: str, course_id: str, skill: dict,
                         lesson_id: str) -> None:
    """Phases 1+2: outline, then per-step content + check, persisted under an
    already-created lesson row. Raises on failure; the caller is responsible
    for marking the row 'failed'.

    Per-step generation (content + its comprehension check) is TWO model
    calls each, and every step is independent of the others — this used to
    run fully serial (up to 2N sequential Bedrock round trips for an N-step
    lesson, the actual cause of guided lessons taking minutes to first open),
    so it is parallelized across steps via map_concurrent. Only the DB
    inserts stay sequential, so `position` is still written in outline order
    regardless of which step's generation happened to finish first.
    """
    context, _ = _context_for(institution_id=institution_id, course_id=course_id, skill=skill)
    outline = _generate_outline(skill=skill, context=context)

    built = map_concurrent(
        lambda step: _build_step_payload(
            institution_id=institution_id, course_id=course_id,
            skill=skill, step=step, context=context,
        ),
        outline,
    )

    for position, payload in enumerate(built):
        content = payload["content"]
        db.insert("guided_lesson_steps", [{
            "lesson_id": lesson_id,
            "position": position,
            "summary": content["summary"],
            "detail_points": content["detail_points"],
            "misconception": content["misconception"],
            "key_takeaway": content["key_takeaway"],
            "bloom_level": payload["bloom_level"],
            "check_item_id": payload["check_item_id"],
        }], prefer="return=minimal")


def load_lesson(*, institution_id: str, lesson_id: str) -> dict:
    """Public entry point when only a lesson_id is in hand (e.g. a future
    caller that doesn't already have the row). Selects the lesson row once,
    then delegates to _assemble_lesson for the steps/checks assembly shared
    with the fast 'ready' path in get_or_generate_lesson, which already has
    the row and skips this select entirely."""
    lessons = db.select("guided_lessons", {
        "id": f"eq.{lesson_id}", "institution_id": f"eq.{institution_id}",
        "select": "id,skill_id,module_ref,title,status", "limit": "1",
    })
    if not lessons:
        raise ValueError(f"lesson {lesson_id} not found")
    return _assemble_lesson(lesson_row=lessons[0], institution_id=institution_id)


def _assemble_lesson(*, lesson_row: dict, institution_id: str) -> dict:
    """Steps + check-item assembly for a lesson row the caller already has.
    Never returns a check item's answer key — the check MCQ is delivered
    like any other item (prompt + choices), and grading happens server-side
    on submit."""
    lesson_id = lesson_row["id"]
    steps = db.select("guided_lesson_steps", {
        "lesson_id": f"eq.{lesson_id}",
        "select": "id,position,summary,detail_points,misconception,"
                  "key_takeaway,bloom_level,check_item_id",
        "order": "position.asc",
    })

    # Pull the client-safe view of every check item in one query (no answer key).
    check_ids = [s["check_item_id"] for s in steps if s.get("check_item_id")]
    checks_by_id: dict[str, dict] = {}
    if check_ids:
        in_list = ",".join(check_ids)
        check_rows = db.select("generated_items", {
            "id": f"in.({in_list})", "institution_id": f"eq.{institution_id}",
            "select": "id,prompt,choices,bloom_level",
        })
        checks_by_id = {r["id"]: r for r in check_rows}

    out_steps = []
    for s in steps:
        check = None
        cid = s.get("check_item_id")
        if cid and cid in checks_by_id:
            c = checks_by_id[cid]
            check = {
                "itemId": c["id"],
                "prompt": c["prompt"],
                "choices": c.get("choices") or [],
            }
        out_steps.append({
            "id": s["id"],
            "position": s["position"],
            "summary": s["summary"],
            "detailPoints": s.get("detail_points") or [],
            "misconception": s.get("misconception"),
            "keyTakeaway": s.get("key_takeaway"),
            "bloomLevel": s.get("bloom_level"),
            "check": check,
        })

    return {
        "lessonId": lesson_row["id"],
        "skillId": lesson_row["skill_id"],
        "moduleRef": lesson_row.get("module_ref"),
        "title": lesson_row["title"],
        "status": lesson_row["status"],
        "steps": out_steps,
    }
