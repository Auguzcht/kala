#!/usr/bin/env python3
"""Read-only review of active same-skill bank pairs at cosine >= 0.90."""
from __future__ import annotations

from collections import Counter

from lesson_check_tools import VectorCache, cosine, materialize_item_vectors, select_all


def main() -> None:
    items = select_all("generated_items", {
        "origin": "eq.bank", "kind": "eq.practice", "retired_at": "is.null",
        "select": "id,skill_id,prompt,embedding,created_at",
    })
    exposures = select_all("item_exposures", {"select": "user_id,item_id"}, order="user_id.asc,item_id.asc")
    counts = Counter(row.get("item_id") for row in exposures)
    vectors = VectorCache()
    materialize_item_vectors(items, vectors)
    by_skill: dict[str, list[dict]] = {}
    for item in items:
        by_skill.setdefault(item["skill_id"], []).append(item)
    high, calibration = [], []
    for skill_items in by_skill.values():
        for index, left in enumerate(skill_items):
            for right in skill_items[index + 1:]:
                score = cosine(left["embedding"], right["embedding"])
                pair = (score, left, right)
                if score >= 0.90:
                    high.append(pair)
                elif 0.85 <= score < 0.90:
                    calibration.append(pair)
    high.sort(key=lambda row: row[0], reverse=True)
    calibration.sort(key=lambda row: row[0], reverse=True)
    print(f"Active bank items: {len(items)}; pairs >= 0.90: {len(high)}")
    for score, left, right in high:
        left_count, right_count = counts[left["id"]], counts[right["id"]]
        if left_count < right_count:
            retire = left
        elif right_count < left_count:
            retire = right
        else:
            retire = max((left, right), key=lambda row: row.get("created_at") or "")
        print(f"\n{score:.6f} skill={left['skill_id']}")
        print(f"  A {left['id']} exposures={left_count}: {left.get('prompt','')}")
        print(f"  B {right['id']} exposures={right_count}: {right.get('prompt','')}")
        print(f"  proposal: retire {retire['id']} ({'fewer exposures' if counts[left['id']] != counts[right['id']] else 'newer on tie'})")
    print(f"\nCalibration pairs 0.85 <= cosine < 0.90: {len(calibration)}")
    for score, left, right in calibration[:10]:
        print(f"\n{score:.6f} skill={left['skill_id']}")
        print(f"  A {left['id']}: {left.get('prompt','')}")
        print(f"  B {right['id']}: {right.get('prompt','')}")
    print(f"\nEmbedding calls this run: {vectors.calls}")
    print("Mode: DRY RUN (read-only)")


if __name__ == "__main__":
    main()
