"""Tiered model router. Cheap default for most Q&A, hints, and RAG answers;
escalate for harder tasks. Keeps model choice in one place."""
from __future__ import annotations

import json

from app.ai import bedrock
from app.ai.reasoning import strip_reasoning
from app.config import get_settings


def get_model_for(task: str) -> str:
    s = get_settings()
    if s.ai_provider == "openrouter":
        models = {
            "fast": s.openrouter_model_fast,
            "tag": s.openrouter_model_fast,
            "default": s.openrouter_model_default,
            "item": s.openrouter_model_item,
            "reasoning": s.openrouter_model_reasoning,
            "premium": s.openrouter_model_premium,
        }
    else:
        models = {
            "fast": s.bedrock_model_fast,
            "tag": s.bedrock_model_fast,
            "default": s.bedrock_model_default,
            "item": s.bedrock_model_default,
            "reasoning": s.bedrock_model_reasoning,
            "premium": s.bedrock_model_premium,
        }
    try:
        return models[task]
    except KeyError as exc:
        raise ValueError(f"unknown model task: {task}") from exc


# Response budget for prose answers (tutor, hints, lesson explanations). The
# old default of 1024 was silently truncating longer explanations mid-sentence
# once a model leaked its reasoning preamble into the content (see
# ai/reasoning.py) — and even without a leak, a "why the other options are
# wrong" explanation legitimately needs more room than a one-liner. Raised to
# a value that comfortably fits a full multi-paragraph answer while staying
# well inside every configured model's context window.
_ANSWER_MAX_TOKENS = 2048


def answer(*, system: str, user_text: str, escalate: bool = False,
           history: list[dict] | None = None) -> str:
    """`history` is prior turns already in bedrock.converse's message shape
    ({"role": "user"|"assistant", "content": [{"text": ...}]}), oldest
    first. Optional and backward-compatible: every existing caller omits
    it and gets exactly the single-turn behavior this function always
    had. Added for the tutor's persistent conversations (Stage 2 of the
    AI overhaul) so a follow-up question can actually reference what was
    said earlier in the same thread, not just the current question alone.

    The reply is post-processed with strip_reasoning() so a leaked
    chain-of-thought preamble never reaches a student (see ai/reasoning.py for
    why this is enforced here rather than left to the prompt)."""
    model = get_model_for("reasoning" if escalate else "default")
    messages = list(history) if history else []
    messages.append({"role": "user", "content": [{"text": user_text}]})
    raw = bedrock.converse(
        model_id=model,
        system=system,
        messages=messages,
        max_tokens=_ANSWER_MAX_TOKENS,
    )
    return strip_reasoning(raw)


def tag_content(*, text: str, skills: list[dict]) -> dict:
    skill_list = [{"id": skill["id"], "name": skill["name"]} for skill in skills]
    raw = bedrock.converse(
        model_id=get_model_for("tag"),
        system=(
            "Tag the supplied course content. Return only JSON with keys "
            "skill_id and bloom_level. skill_id must be one of the supplied IDs "
            "or null; bloom_level must be one of remember, understand, apply, "
            "analyze, evaluate, create or null."
        ),
        messages=[{"role": "user", "content": [{"text": json.dumps({
            "skills": skill_list, "content": text,
        })}]}],
        max_tokens=256,
    )
    normalized = raw.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(normalized)
    except json.JSONDecodeError:
        return {"skill_id": None, "bloom_level": None}
    skill_ids = {skill["id"] for skill in skills}
    bloom_levels = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
    return {
        "skill_id": result.get("skill_id") if result.get("skill_id") in skill_ids else None,
        "bloom_level": result.get("bloom_level") if result.get("bloom_level") in bloom_levels else None,
    }
