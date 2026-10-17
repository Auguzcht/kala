"""Small pgvector parsing and cosine helpers shared by worker jobs."""
from __future__ import annotations

import json
import math


def parse_vector(value) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, (list, tuple)) or not value:
        return None
    return [float(x) for x in value]


def cosine(a, b) -> float:
    left, right = parse_vector(a), parse_vector(b)
    if left is None or right is None or len(left) != len(right):
        return -1.0
    dot = sum(x * y for x, y in zip(left, right))
    norm_left = math.sqrt(sum(x * x for x in left))
    norm_right = math.sqrt(sum(x * x for x in right))
    return dot / (norm_left * norm_right) if norm_left and norm_right else -1.0
