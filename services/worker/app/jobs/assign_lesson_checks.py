"""Resumable assignment of active bank checks to one lesson's steps."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.db import supabase as db
from app.embed import embed
from app.lesson_matching import assign_matches, step_text
from app.vector_utils import parse_vector

logger = logging.getLogger("kala.worker")


def run(*, lesson_id: str, institution_id: str | None = None) -> dict:
    lessons = db.select("guided_lessons", {
        "id": f"eq.{lesson_id}", "select": "id,course_id,skill_id", "limit": "1",
    })
    if not lessons:
        return {"lesson_id": lesson_id, "assigned": 0, "missing": True}
    lesson = lessons[0]
    steps = db.select("guided_lesson_steps", {
        "lesson_id": f"eq.{lesson_id}",
        "select": "id,position,summary,detail_points,bloom_level,check_item_id,embedding",
        "order": "position.asc",
    })
    embedded_steps = []
    embedded_count = 0
    for step in steps:
        vector = parse_vector(step.get("embedding"))
        if vector is None:
            text = step_text(step)
            if not text.strip():
                continue
            vector = embed(text)
            if len(vector) != 1024:
                raise ValueError(f"embedding dimension {len(vector)}, expected 1024")
            db.update("guided_lesson_steps", {"id": f"eq.{step['id']}", "embedding": "is.null"},
                      {"embedding": vector})
            step["embedding"] = vector
            embedded_count += 1
        embedded_steps.append(step)

    items = db.select("generated_items", {
        "course_id": f"eq.{lesson['course_id']}", "skill_id": f"eq.{lesson['skill_id']}",
        "kind": "eq.practice", "origin": "eq.bank", "retired_at": "is.null",
        "embedding": "not.is.null",
        "select": "id,prompt,bloom_level,embedding",
        "order": "created_at.asc", "limit": "1000",
    })
    assignments = assign_matches(
        embedded_steps, items,
        existing_ids={step["check_item_id"] for step in steps if step.get("check_item_id")},
    )
    assigned = 0
    for step in steps:
        match = assignments.get(step["id"])
        if not match:
            continue
        item_id, score = match
        updated = db.update("guided_lesson_steps", {
            "id": f"eq.{step['id']}", "check_item_id": "is.null",
        }, {"check_item_id": item_id})
        if updated:
            assigned += 1
        logger.info("lesson check assigned lesson_id=%s step_id=%s item_id=%s score=%.4f",
                    lesson_id, step["id"], item_id, score)
    return {"lesson_id": lesson_id, "steps": len(steps), "embedded": embedded_count,
            "assigned": assigned, "remaining": sum(not s.get("check_item_id") for s in steps)}
