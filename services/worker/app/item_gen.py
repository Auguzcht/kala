"""Worker-side RAG-grounded MCQ generation.

This is a deliberate trimmed duplicate of ``services/api/app/learn/items.py``.
The worker image only copies its own ``app/`` tree, so the async item job
cannot import the API generator. Keep the prompt, response schema, banned
phrases, context rules, and 2,048-token budget in sync with the API copy;
grep both files for ``_MCQ_SYSTEM`` and ``_MCQ_RESPONSE_FORMAT`` before
changing either one.

The one intentional behavior difference is the validation reroll: the API
caller retries validation unconditionally once, while this worker copy only
rerolls when at least 85 seconds remain in the item job's 100-second budget.
At the measured 51-82 second item latency, almost every validation failure is
therefore retried by the next scheduled queue attempt instead of spending the
remaining invocation budget.
"""
from __future__ import annotations

import json
import logging
import time

import httpx

from app import rag
from app.config import get_settings
from app.db import supabase as db

logger = logging.getLogger("kala.worker")

# Keep this prompt byte-for-byte aligned with services/api/app/learn/items.py.
_MCQ_SYSTEM = (
    "You write a single multiple-choice question that tests whether a student "
    "KNOWS a course concept. The supplied source_material is the ground truth "
    "your question must agree with — it is NOT something the student is "
    "reading. Write the question as if the student must already know the fact, "
    "not look it up.\n\n"
    "Return strict JSON and nothing else: "
    '{"prompt": str, "choices": [{"id": "a".."d", "label": str}], '
    '"correct_choice_id": str, "explanation": str}. '
    "Write exactly four choices with exactly one correct.\n\n"
    "FORBIDDEN in the prompt and in every choice — never refer to the "
    "material itself or to a source. Do not write the words or phrases "
    "\"excerpt\", \"passage\", \"text\", \"reading\", \"overview\", "
    "\"document\", \"module\", \"chapter\", \"according to\", \"the "
    "reading states\", \"as mentioned\", \"the author\", \"the material\", "
    "or \"this section\", and do not otherwise frame the question as "
    "\"what does X say/explain/list\". A question that only works if the "
    "student can see the source is a bad question.\n\n"
    "Match the requested bloom_level: at remember/understand levels ask "
    "directly about the concept; at apply/analyze/evaluate levels, when the "
    "material supports it, frame a short concrete scenario the student must "
    "reason about. Distractors must be plausible to someone who does NOT "
    "know the concept — common misconceptions, not obviously-wrong filler.\n\n"
    "Ground every fact in the source_material: do not invent facts, numbers, "
    "or terminology that are not supported by it."
)

_BANNED_STEM_PHRASES = (
    "according to",
    "excerpt",
    "passage",
    "the reading",
    "as mentioned",
    "the author",
    "the material",
    "this section",
    "the document",
    "the module",
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

_RETRIEVAL_K = 5
_MAX_CONTEXT_CHARS = 12000
_MAX_TOKENS = 2048
_MIN_REMAINING_FOR_REROLL = 85.0


class ItemGenerationError(RuntimeError):
    """Raised when model output cannot form a safe study item."""


class NoCourseContentError(ItemGenerationError):
    """The skill has no grounded course content yet; the queue should retry."""

    def __init__(self, *, skill_name: str):
        super().__init__(
            f'Kala has no course material for "{skill_name}" yet, so it cannot '
            "write questions for it. Course content needs to be ingested first."
        )
        self.skill_name = skill_name


def _find_banned_phrase(text: str) -> str | None:
    lowered = text.lower()
    for phrase in _BANNED_STEM_PHRASES:
        if phrase in lowered:
            return phrase
    return None


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
    banned = _find_banned_phrase(prompt)
    if banned:
        raise ValueError(f"generated prompt is meta-referential (contains {banned!r})")
    if not isinstance(choices, list) or len(choices) != 4:
        raise ValueError("generated item must contain exactly four choices")
    if not isinstance(correct_choice_id, str) or not isinstance(explanation, str):
        raise ValueError(  # noqa: TRY004 — model-output validation uses one exception type.
            "generated item has invalid answer metadata"
        )

    expected_ids = {"a", "b", "c", "d"}
    actual_ids: set[str] = set()
    validated: list[dict[str, str]] = []
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError(  # noqa: TRY004 — model-output validation uses one exception type.
                "generated choice must be an object"
            )
        choice_id, label = choice.get("id"), choice.get("label")
        if not isinstance(choice_id, str) or not isinstance(label, str) or not label.strip():
            raise ValueError("generated choice is missing an id or label")
        banned_choice = _find_banned_phrase(label)
        if banned_choice:
            raise ValueError(f"generated choice is meta-referential (contains {banned_choice!r})")
        actual_ids.add(choice_id)
        validated.append({"id": choice_id, "label": label.strip()})
    if actual_ids != expected_ids or correct_choice_id not in expected_ids:
        raise ValueError("generated choices must be a, b, c, and d")
    return prompt.strip(), validated, correct_choice_id, explanation.strip()


def _context_for(*, institution_id: str, course_id: str, skill: dict) -> list[str]:
    chunks = rag.retrieve(
        institution_id=institution_id, course_id=course_id,
        query=skill["name"], k=_RETRIEVAL_K,
    )
    texts = [(chunk.get("chunk_text") or "").strip() for chunk in chunks]
    texts = [text for text in texts if text]
    if not texts:
        raise NoCourseContentError(skill_name=skill.get("name") or "this skill")
    return texts


def _rotated_context(chunks: list[str], offset: int) -> str:
    if not chunks:
        raise ValueError("_rotated_context requires at least one chunk")
    start = offset % len(chunks)
    ordered = chunks[start:] + chunks[:start]
    joined = "\n---\n".join(ordered)
    if len(joined) > _MAX_CONTEXT_CHARS:
        joined = joined[:_MAX_CONTEXT_CHARS].rsplit("\n---\n", 1)[0] or joined[:_MAX_CONTEXT_CHARS]
    return joined


def _content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content") or ""


def _call_and_validate(*, skill: dict, context: str, timeout_seconds: float) -> tuple[str, list[dict[str, str]], str, str]:
    settings = get_settings()
    payload = {
        "model": settings.openrouter_model_item,
        "messages": [
            {"role": "system", "content": _MCQ_SYSTEM},
            {"role": "user", "content": json.dumps({
                "skill": skill["name"],
                "bloom_level": skill.get("bloom_level"),
                "source_material": context,
            })},
        ],
        "max_tokens": _MAX_TOKENS,
        "response_format": _MCQ_RESPONSE_FORMAT,
    }
    with httpx.Client(
        base_url=settings.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala",
        },
        timeout=timeout_seconds,
    ) as client:
        response = client.post("/chat/completions", json=payload)
        response.raise_for_status()
        raw = _content(response.json())
    if not raw.strip():
        raise ValueError("item model returned empty content")
    return _validated_mcq(raw)


def generate_question(
    *, institution_id: str, course_id: str, skill: dict, kind: str,
    job_id: str, set_id: str | None = None, context_offset: int = 0,
    deadline: float, call_timeout_seconds: float,
) -> dict:
    """Generate and persist one item using the queue id as a stable item id.

    Reusing ``job_id`` as the generated item's id makes the persist-then-
    checkpoint gap recoverable: a later run can find the item by id and mark
    the queue row complete without making another model call.
    """
    context = _rotated_context(
        _context_for(institution_id=institution_id, course_id=course_id, skill=skill),
        context_offset,
    )

    def call() -> tuple[str, list[dict[str, str]], str, str]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("item generation budget exhausted")
        return _call_and_validate(
            skill=skill, context=context,
            timeout_seconds=min(call_timeout_seconds, remaining),
        )

    try:
        try:
            prompt, choices, correct_choice_id, explanation = call()
        except (httpx.HTTPError, TimeoutError) as first_exc:
            # Provider/transport failures never reroll in this invocation.
            raise ItemGenerationError("item model transport failed") from first_exc
        except Exception as first_exc:
            # Intentional worker-only difference from the API copy: a
            # validation reroll is allowed only with >=85 seconds left in the
            # 100-second job budget. The API copy retries validation
            # unconditionally; this copy must not spend the worker's remaining
            # budget on a second long call.
            if deadline - time.monotonic() < _MIN_REMAINING_FOR_REROLL:
                raise ItemGenerationError("item validation failed within budget") from first_exc
            try:
                prompt, choices, correct_choice_id, explanation = call()
            except Exception as reroll_exc:
                raise ItemGenerationError("validation reroll failed") from reroll_exc
    except NoCourseContentError:
        raise
    except ItemGenerationError:
        raise
    except Exception as exc:
        raise ItemGenerationError("item model call failed") from exc

    row = {
        "id": job_id,
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
        row["set_id"] = set_id
    db.insert("generated_items", [row])
    return {
        "id": job_id,
        "skillId": skill["id"],
        "bloomLevel": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
    }
