#!/usr/bin/env python3
"""Add the read-only top-20 retrieval audit to an existing benchmark run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.ai import rag  # noqa: E402
from app.db import supabase as db  # noqa: E402

COURSE_ID = "ae4e7680-f94b-4652-b3f6-b9c32f4420de"
RAW = ROOT / "scripts/bench/out/batch_items.raw.json"
REPORT = ROOT / "docs/bugs/batch-generation-benchmark.md"


def main() -> None:
    result = json.loads(RAW.read_text())
    threshold = float(result["threshold"]["threshold"])
    course = db.select("courses", {"id": f"eq.{COURSE_ID}", "select": "institution_id", "limit": "1"})[0]
    skills = db.select("skills", {
        "course_id": f"eq.{COURSE_ID}",
        "institution_id": f"eq.{course['institution_id']}",
        "status": "eq.approved",
        "select": "id,name",
        "order": "created_at.asc",
    })
    top20 = []
    for skill in skills:
        tagged = db.select("content_items", {
            "course_id": f"eq.{COURSE_ID}",
            "skill_id": f"eq.{skill['id']}",
            "select": "id",
            "limit": "1000",
        })
        matches = rag.retrieve(
            institution_id=course["institution_id"],
            course_id=COURSE_ID,
            query=skill["name"],
            k=20,
        )
        rows = []
        for rank, match in enumerate(matches, 1):
            match_skill = match.get("skill_id")
            label = "same_skill" if match_skill == skill["id"] else ("null_skill" if match_skill is None else "different_skill")
            rows.append({
                "rank": rank,
                "content_item_id": match.get("id"),
                "similarity": float(match.get("similarity") or 0.0),
                "label": label,
                "above_threshold": float(match.get("similarity") or 0.0) >= threshold,
            })
        top20.append({"skill_id": skill["id"], "skill_name": skill["name"], "tagged_chunk_count": len(tagged), "matches": rows})

    by_id = {row["skill_id"]: row for row in top20}
    for row in result["retrieval_summary"]:
        if row["id"] in by_id:
            row["tagged_chunk_count"] = by_id[row["id"]]["tagged_chunk_count"]
    result["retrieval_top20"] = top20
    result["threshold"]["note"] = (
        "This is the maximum-Youden labeled cutoff. Tag labels are visibly noisy: "
        "the highest-scoring retrieved rows are often tagged to another skill, so "
        "the cutoff is a retrieval inclusion rule, not proof of semantic correctness."
    )
    RAW.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    lines = REPORT.read_text().splitlines()
    marker = "### Top-20 match_content_items results"
    if marker not in lines:
        insert_at = lines.index("### Similarity distribution")
        block = ["### Top-20 match_content_items results", "", "Scores are listed without chunk text or student data; `same_skill`, `different_skill`, and `null_skill` are based on the current `skill_id` tag.", ""]
        for skill in top20:
            block += [f"#### {skill['skill_name']}", "", "| Rank | Similarity | Label | Included at threshold | Content item |", "|---:|---:|---|---|---|"]
            for row in skill["matches"]:
                block.append(f"| {row['rank']} | {row['similarity']:.6f} | {row['label']} | {'yes' if row['above_threshold'] else 'no'} | `{row['content_item_id']}` |")
            block.append("")
        lines[insert_at:insert_at] = block
    REPORT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
