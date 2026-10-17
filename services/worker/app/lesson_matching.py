"""Pure lesson-check matching rules, shared by the worker and dry-run tools."""
from __future__ import annotations

from app.bank_config import LESSON_CHECK_DUP_COSINE, LESSON_CHECK_MIN_SCORE
from app.vector_utils import cosine, parse_vector


def step_text(step: dict) -> str:
    title = step.get("title") or step.get("summary") or ""
    points = step.get("detail_points") or []
    if isinstance(points, str):
        points = [points]
    return "\n".join(str(value) for value in [title, step.get("summary") or "", *points]
                     if str(value).strip())


def assign_matches(steps: list[dict], items: list[dict], *, existing_ids: set[str] | None = None,
                   min_score: float = LESSON_CHECK_MIN_SCORE,
                   duplicate_cosine: float = LESSON_CHECK_DUP_COSINE) -> dict[str, tuple[str, float]]:
    """Greedily assign globally best step/item pairs and remove near duplicates."""
    remaining = [item for item in items if parse_vector(item.get("embedding")) is not None]
    assignments: dict[str, tuple[str, float]] = {}
    used = set(existing_ids or ())
    for item_id in used:
        chosen = next((item for item in remaining if item.get("id") == item_id), None)
        if chosen:
            vector = chosen["embedding"]
            remaining = [item for item in remaining if item.get("id") != item_id and
                         cosine(vector, item.get("embedding")) < duplicate_cosine]
    open_steps = [step for step in steps if not step.get("check_item_id")]
    while open_steps and remaining:
        best = None
        for step in open_steps:
            step_vector = step.get("embedding")
            if parse_vector(step_vector) is None:
                continue
            for item in remaining:
                score = cosine(step_vector, item.get("embedding"))
                if step.get("bloom_level") and step.get("bloom_level") == item.get("bloom_level"):
                    score += 0.05
                if best is None or score > best[0]:
                    best = (score, step, item)
        if best is None or best[0] < min_score:
            break
        score, step, item = best
        assignments[step["id"]] = (item["id"], score)
        open_steps.remove(step)
        used.add(item["id"])
        vector = item["embedding"]
        remaining = [candidate for candidate in remaining
                     if candidate.get("id") != item["id"] and
                     cosine(vector, candidate.get("embedding")) < duplicate_cosine]
    return assignments
