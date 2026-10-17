"""Shared read-only data and local embedding-cache helpers for lesson tools."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/worker"))

from app.db import supabase as db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.embed import embed  # noqa: E402
from app.lesson_matching import assign_matches, step_text  # noqa: E402
from app.vector_utils import cosine, parse_vector  # noqa: E402


class VectorCache:
    def __init__(self, path: str = "/tmp/kala-bank-quality-vectors.json"):
        self.path = Path(path)
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        settings = get_settings()
        provider = settings.embed_provider or settings.ai_provider
        model = getattr(settings, {"openai": "openai_embed_model",
                                  "openrouter": "openrouter_embed_model"}.get(provider,
                                                                               "bedrock_embed_model"))
        self.namespace = f"worker:{provider}:{model}:search_document:1024"
        self.calls = 0

    def get(self, text: str) -> list[float]:
        key = hashlib.sha256((self.namespace + "\0" + text).encode()).hexdigest()
        if key in self.cache:
            return parse_vector(self.cache[key])
        vector = parse_vector(embed(text, input_type="search_document"))
        if not vector or len(vector) != 1024:
            raise ValueError(f"expected 1024-dimensional embedding for {text[:60]!r}")
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            raise ValueError("embedding has zero norm")
        vector = [value / norm for value in vector]
        self.cache[key] = vector
        self.cache["_embedding_function_calls"] = int(self.cache.get("_embedding_function_calls", 0)) + 1
        self.calls += 1
        self.path.write_text(json.dumps(self.cache))
        return vector


def select_all(table: str, params: dict[str, str], *, order: str = "id.asc") -> list[dict]:
    rows = []
    while True:
        page = db.select(table, {**params, "order": order, "limit": "1000",
                                 "offset": str(len(rows))})
        rows.extend(page)
        if len(page) < 1000:
            return rows


def lesson_and_steps(lesson: dict) -> tuple[dict, list[dict]]:
    steps = select_all("guided_lesson_steps", {
        "lesson_id": f"eq.{lesson['id']}",
        "select": "id,position,summary,detail_points,misconception,key_takeaway,bloom_level,check_item_id,embedding",
    })
    steps.sort(key=lambda step: int(step.get("position") or 0))
    return lesson, steps


def materialize_step_vectors(steps: list[dict], vectors: VectorCache) -> None:
    for step in steps:
        if parse_vector(step.get("embedding")) is None:
            step["embedding"] = vectors.get(step_text(step))


def materialize_item_vectors(items: list[dict], vectors: VectorCache) -> None:
    for item in items:
        if parse_vector(item.get("embedding")) is None:
            item["embedding"] = vectors.get(item.get("prompt") or "")


def current_and_new_assignments(lesson: dict, steps: list[dict], vectors: VectorCache):
    materialize_step_vectors(steps, vectors)
    items = select_all("generated_items", {
        "course_id": f"eq.{lesson['course_id']}", "skill_id": f"eq.{lesson['skill_id']}",
        "kind": "eq.practice", "origin": "eq.bank", "retired_at": "is.null",
        "select": "id,prompt,bloom_level,embedding,created_at",
    })
    materialize_item_vectors(items, vectors)
    assignments = assign_matches(steps, items,
                                 existing_ids={s["check_item_id"] for s in steps if s.get("check_item_id")})
    check_ids = [s["check_item_id"] for s in steps if s.get("check_item_id")]
    checks = select_all("generated_items", {
        "id": f"in.({','.join(check_ids)})" if check_ids else "in.(00000000-0000-0000-0000-000000000000)",
        "select": "id,prompt,bloom_level,embedding",
    })
    checks_by_id = {row["id"]: row for row in checks}
    for row in checks:
        if parse_vector(row.get("embedding")) is None:
            row["embedding"] = vectors.get(row.get("prompt") or "")
    old = {}
    for step in steps:
        item_id = step.get("check_item_id")
        item = checks_by_id.get(item_id)
        old[step["id"]] = (item, cosine(step.get("embedding"), item.get("embedding")) +
                            (0.05 if item.get("bloom_level") == step.get("bloom_level") else 0.0)) if item else (None, None)
    return items, old, assignments
