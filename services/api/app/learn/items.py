"""Shared item generation and grading for the learn loop (diagnostic,
practice, flashcards). One RAG-grounded generator, three surfaces call it.

Correct answers never leave the server: every item is persisted with its
answer key on creation, the client only ever gets the sanitized view, and
submissions are graded by looking the item back up, not by trusting a
client-supplied "correct" flag.
"""
from __future__ import annotations

import json
import logging

from app.ai import bedrock, rag
from app.ai.errors import ModelUnavailableError
from app.ai.router import get_model_for
from app.db import supabase as db

logger = logging.getLogger(__name__)

_MCQ_SYSTEM = (
    "You write a single multiple-choice question grounded ONLY in the "
    "supplied course excerpt. Return strict JSON and nothing else: "
    '{"prompt": str, "choices": [{"id": "a".."d", "label": str}], '
    '"correct_choice_id": str, "explanation": str}. '
    "Write exactly four choices with exactly one correct. Do not invent "
    "facts that are not supported by the excerpt."
)

_MCQ_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "study_question",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "choices": {
                    "type": "array",
                    "minItems": 4,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                            "label": {"type": "string"},
                        },
                        "required": ["id", "label"],
                        "additionalProperties": False,
                    },
                },
                "correct_choice_id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                "explanation": {"type": "string"},
            },
            "required": ["prompt", "choices", "correct_choice_id", "explanation"],
            "additionalProperties": False,
        },
    },
}


class ItemGenerationError(RuntimeError):
    """Raised when model output cannot form a safe study item."""


class NoCourseContentError(ItemGenerationError):
    """The skill has no grounded course content to build a question from.

    A subclass of ItemGenerationError so every existing caller/handler that
    already maps that to a clean 502 keeps working, while routers that want to
    say something more specific ("no material for this skill yet" rather than
    "could not create a question") can catch this narrower type. The message
    is student-facing: it names the missing prerequisite rather than blaming
    the model.
    """

    def __init__(self, *, skill_name: str):
        super().__init__(
            f"Kala has no course material for \"{skill_name}\" yet, so it can't "
            "write questions for it. Course content needs to be ingested first."
        )
        self.skill_name = skill_name


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def _validated_mcq(raw: str) -> tuple[str, list[dict[str, str]], str, str]:
    parsed = _parse_json(raw)
    prompt = parsed.get("prompt")
    choices = parsed.get("choices")
    correct_choice_id = parsed.get("correct_choice_id")
    explanation = parsed.get("explanation", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("generated item is missing a prompt")
    if not isinstance(choices, list) or len(choices) != 4:
        raise ValueError("generated item must contain exactly four choices")
    if not isinstance(correct_choice_id, str) or not isinstance(explanation, str):
        raise ValueError("generated item has invalid answer metadata")

    expected_ids = {"a", "b", "c", "d"}
    actual_ids: set[str] = set()
    validated: list[dict[str, str]] = []
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("generated choice must be an object")
        choice_id, label = choice.get("id"), choice.get("label")
        if not isinstance(choice_id, str) or not isinstance(label, str) or not label.strip():
            raise ValueError("generated choice is missing an id or label")
        actual_ids.add(choice_id)
        validated.append({"id": choice_id, "label": label.strip()})
    if actual_ids != expected_ids or correct_choice_id not in expected_ids:
        raise ValueError("generated choices must be a, b, c, and d")
    return prompt.strip(), validated, correct_choice_id, explanation.strip()


def _context_for(*, institution_id: str, course_id: str, skill: dict) -> str:
    """Grounded course text for a skill, or raise if there is none.

    This USED to fall back to `skill["name"]` when retrieval came back empty,
    with a comment about "degrading gracefully rather than hard-failing the
    learn loop". That was the wrong trade: it turned a loud, visible
    misconfiguration into SILENT GARBAGE. With no excerpt, the model is asked
    to write an evaluative MCQ grounded in a single sentence, so it rewords
    that sentence into a stem, makes the skill's own phrase the correct answer
    every time ("operational and cost trade-offs"), and invents nonsense
    distractors ("social media engagement metrics") because it has no facts to
    draw plausible wrong answers from. Every item passes schema validation, so
    nothing flagged it — the questions were simply meaningless, which is the
    worst possible failure for a student studying for board exams.

    A course with skills but no content_items is a setup error (ingest has not
    run), not a runtime condition to paper over. Fail it here, at the source,
    so every caller surfaces "no material yet" instead of shipping plausible-
    looking questions with no substance.
    """
    chunks = rag.retrieve(
        institution_id=institution_id, course_id=course_id, query=skill["name"], k=3,
    )
    # Filter to chunks that actually carry text BEFORE joining. Joining first
    # and stripping the result is not enough: blank chunks still contribute
    # separators, so "  " + "" join to "   \n---\n" which survives a strip and
    # reads as grounded content.
    texts = [(c.get("chunk_text") or "").strip() for c in chunks]
    texts = [t for t in texts if t]
    if not texts:
        raise NoCourseContentError(skill_name=skill.get("name") or "this skill")
    return "\n---\n".join(texts)


def _call_and_validate(*, skill: dict, context: str) -> tuple[str, list[dict[str, str]], str, str]:
    """One model call, parsed and validated. Raises on anything unusable —
    a transport failure, a malformed/truncated body, or a semantically invalid
    MCQ. The caller decides whether to try again."""
    raw = bedrock.converse(
        model_id=get_model_for("item"),
        system=_MCQ_SYSTEM,
        messages=[{"role": "user", "content": [{"text": json.dumps({
            "skill": skill["name"], "bloom_level": skill.get("bloom_level"),
            "excerpt": context,
        })}]}],
        max_tokens=1536,
        response_format=_MCQ_RESPONSE_FORMAT,
    )
    return _validated_mcq(raw)


def generate_question(*, institution_id: str, course_id: str, skill: dict, kind: str,
                      set_id: str | None = None) -> dict:
    """Generate one RAG-grounded MCQ for a skill, persist it with its answer
    key, and return only the client-safe view.

    `set_id` groups the item under a quiz_sets row (batch practice generation,
    see routers/practice.py). Optional and backward-compatible: every existing
    caller omits it and gets an ungrouped item exactly as before. Threaded into
    the insert rather than patched after, so an item is never briefly persisted
    outside the set it was generated for.

    One bounded retry on a VALIDATION failure. This is a distinct failure mode
    from the transport/capability retry inside bedrock.converse: that one
    catches a call that could not be delivered (5xx, timeout, structured-output
    rejection). Here the HTTP call succeeded but the body was unusable —
    malformed or truncated JSON, or a semantically wrong MCQ — which
    _validated_mcq rejects. Those are independent events, so they get
    independent retries; a free-tier model that returns garbage once will very
    often return a good item on a second roll, and without this the failure
    propagates straight out of map_concurrent (which is all-or-nothing by
    design) and 502s an entire batch because ONE of five concurrent rolls was
    bad. Retried once, never looped: a model that fails twice in a row is a
    real signal, not something to keep hammering.
    """
    context = _context_for(institution_id=institution_id, course_id=course_id, skill=skill)
    try:
        try:
            prompt, choices, correct_choice_id, explanation = _call_and_validate(
                skill=skill, context=context,
            )
        except ModelUnavailableError:
            # A provider-side failure (429, 5xx, timeout, retired model). This
            # is NOT a validation failure: bedrock.converse already gave it one
            # cross-provider fallback attempt, and retrying it here would just
            # hammer the same rate limit a second time. Surface it as-is.
            raise
        except Exception as first_exc:
            logger.warning(
                "Generated item failed validation, retrying once "
                "(course=%s skill=%s kind=%s): %s",
                course_id, skill.get("id"), kind, first_exc,
            )
            prompt, choices, correct_choice_id, explanation = _call_and_validate(
                skill=skill, context=context,
            )
    except Exception as exc:
        logger.error(
            "Refusing to store an invalid generated item (course=%s skill=%s kind=%s): %s",
            course_id,
            skill.get("id"),
            kind,
            exc,
        )
        raise ItemGenerationError(
            "Kala could not create a valid question. Please try again."
        ) from exc

    item_row = {
        "institution_id": institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "kind": kind,
        "bloom_level": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
        "correct_choice_id": correct_choice_id,
        "explanation": explanation,
    }
    if set_id is not None:
        item_row["set_id"] = set_id
    rows = db.insert("generated_items", [item_row])
    item = rows[0]
    return {
        "id": item["id"],
        "skillId": skill["id"],
        "bloomLevel": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
    }


def grade(*, institution_id: str, item_id: str, choice_id: str) -> dict:
    """Look up the stored answer key and grade server-side."""
    rows = db.select("generated_items", {
        "id": f"eq.{item_id}", "institution_id": f"eq.{institution_id}",
        "select": "id,skill_id,course_id,correct_choice_id,explanation,set_id", "limit": "1",
    })
    if not rows:
        raise ValueError(f"item {item_id} not found")
    item = rows[0]
    correct = choice_id == item["correct_choice_id"]
    return {
        "skillId": item["skill_id"],
        "courseId": item["course_id"],
        "correct": correct,
        "explanation": item.get("explanation") or "",
        # Which quiz set this item belonged to, if any. Ungrouped items
        # (/next, flashcards, tutor checks) have set_id null and the caller
        # (practice.submit) simply skips the attempt bookkeeping for them.
        "setId": item.get("set_id"),
    }


def correct_label(item: dict) -> str | None:
    """The label of an item's correct choice, or None if choices/answer are
    missing (defensive — bad data degrades to a null label, never a crash).

    This is the one place that resolves an answer key to a human-readable
    label. Study mode's flip-back uses it (see routers/flashcards.py), so the
    flashcard deck never has to re-implement the lookup. It does NOT leak a
    full answer key: it returns a single label string, which the study
    endpoint is allowed to show; grading still happens server-side against
    correct_choice_id, never against this label.
    """
    choices = item.get("choices") or []
    return next(
        (c.get("label") for c in choices if c.get("id") == item.get("correct_choice_id")),
        None,
    )


def weakest_skill(*, institution_id: str, user_id: str, course_id: str) -> dict | None:
    """Pick the skill this student is weakest on for practice: lowest
    mastery estimate, with never-attempted skills ranked weakest of all."""
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level",
    })
    if not skills:
        return None
    mastery = db.select("mastery_state", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate",
    })
    estimates = {m["skill_id"]: float(m["estimate"]) for m in mastery}
    return min(skills, key=lambda s: estimates.get(s["id"], -1.0))
