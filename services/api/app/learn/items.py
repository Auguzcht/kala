"""Shared item generation and grading for the learn loop (diagnostic,
practice, flashcards). One RAG-grounded generator, three surfaces call it.

Correct answers never leave the server: every item is persisted with its
answer key on creation, the client only ever gets the sanitized view, and
submissions are graded by looking the item back up, not by trusting a
client-supplied "correct" flag.
"""
from __future__ import annotations

import json

from app.ai import bedrock, rag
from app.ai.router import get_model_for
from app.db import supabase as db

_MCQ_SYSTEM = (
    "You write a single multiple-choice question grounded ONLY in the "
    "supplied course excerpt. Return strict JSON and nothing else: "
    '{"prompt": str, "choices": [{"id": "a".."d", "label": str}], '
    '"correct_choice_id": str, "explanation": str}. '
    "Write exactly four choices with exactly one correct. Do not invent "
    "facts that are not supported by the excerpt."
)



def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def _context_for(*, institution_id: str, course_id: str, skill: dict) -> str:
    chunks = rag.retrieve(
        institution_id=institution_id, course_id=course_id, query=skill["name"], k=3,
    )
    if chunks:
        return "\n---\n".join(c.get("chunk_text", "") for c in chunks)
    # No embedded content for this skill yet (e.g. ingest hasn't run): degrade
    # gracefully to the skill name rather than hard-failing the learn loop.
    return skill["name"]


def generate_question(*, institution_id: str, course_id: str, skill: dict, kind: str) -> dict:
    """Generate one RAG-grounded MCQ for a skill, persist it with its answer
    key, and return only the client-safe view."""
    context = _context_for(institution_id=institution_id, course_id=course_id, skill=skill)
    try:
        raw = bedrock.converse(
            model_id=get_model_for("default"),
            system=_MCQ_SYSTEM,
            messages=[{"role": "user", "content": [{"text": json.dumps({
                "skill": skill["name"], "bloom_level": skill.get("bloom_level"),
                "excerpt": context,
            })}]}],
            max_tokens=512,
        )
        parsed = _parse_json(raw)
        choices = parsed["choices"]
        if not isinstance(choices, list) or len(choices) < 2:
            raise ValueError("model returned fewer than 2 choices")
        prompt = parsed["prompt"]
        correct_choice_id = parsed["correct_choice_id"]
        explanation = parsed.get("explanation", "")
    except Exception:
        # Deterministic fallback keeps the loop usable if generation fails
        # (model error, malformed JSON, no Bedrock access in this env).
        prompt = f"Which statement best matches: {skill['name']}?"
        choices = [
            {"id": "a", "label": skill["name"]},
            {"id": "b", "label": "None of the above"},
        ]
        correct_choice_id = "a"
        explanation = ""

    rows = db.insert("generated_items", [{
        "institution_id": institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "kind": kind,
        "bloom_level": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
        "correct_choice_id": correct_choice_id,
        "explanation": explanation,
    }])
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
        "select": "id,skill_id,course_id,correct_choice_id,explanation", "limit": "1",
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
    }


def reveal(*, institution_id: str, item_id: str) -> dict:
    """Look up an item's answer key WITHOUT a client choice — the pre-commit
    Show Answer path. This is deliberately a separate function from grade(),
    not grade() called with some sentinel choice_id: the caller (the reveal
    endpoint) always treats a reveal as a lapse regardless of what this
    returns, so the two must stay distinguishable in the code, not just in
    intent. Still never trusts the client with anything beyond the single
    correct label — choices/prompt aren't needed here, the client already has
    them from the deck response."""
    rows = db.select("generated_items", {
        "id": f"eq.{item_id}", "institution_id": f"eq.{institution_id}",
        "select": "id,skill_id,course_id,correct_choice_id,explanation,choices", "limit": "1",
    })
    if not rows:
        raise ValueError(f"item {item_id} not found")
    item = rows[0]
    choices = item.get("choices") or []
    correct_label = next(
        (c["label"] for c in choices if c.get("id") == item["correct_choice_id"]), None,
    )
    return {
        "skillId": item["skill_id"],
        "courseId": item["course_id"],
        "correctChoiceId": item["correct_choice_id"],
        "correctLabel": correct_label,
        "explanation": item.get("explanation") or "",
    }


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
