"""Course-wide, idempotent embedding tag recomputation.

The comparison and write happen in one Postgres RPC per course. This job
never constructs an AI client and deliberately leaves the legacy tagger in the
repository until the E4 cleanup.
"""
from __future__ import annotations

import logging

from app import tag_config
from app.db import supabase as db

logger = logging.getLogger("kala.worker.tag_recompute")


def run(*, course_id: str | None = None, institution_id: str | None = None) -> dict:
    courses = []
    if course_id:
        courses = db.select("courses", {
            "id": f"eq.{course_id}",
            **({"institution_id": f"eq.{institution_id}"} if institution_id else {}),
            "select": "id,institution_id",
            "limit": "1",
        })
    else:
        courses = db.select("courses", {
            **({"institution_id": f"eq.{institution_id}"} if institution_id else {}),
            "select": "id,institution_id",
            "limit": "1000",
        })

    totals = {"courses": 0, "tagged": 0, "below_threshold": 0,
              "ambiguous": 0, "changed": 0, "gap_filled": 0}
    for course in courses:
        approved = db.select("skills", {
            "course_id": f"eq.{course['id']}",
            "institution_id": f"eq.{course['institution_id']}",
            "status": "eq.approved",
            "select": "id,name,embedding",
        })
        if not approved:
            continue
        for skill in approved:
            if skill.get("embedding") is None:
                logger.warning("tag_recompute skill_missing_embedding course_id=%s skill_id=%s name=%s",
                               course["id"], skill["id"], skill.get("name"))
        result = db.rpc("recompute_embedding_tags", {
            "p_course_id": course["id"],
            "p_threshold": tag_config.TAG_THRESHOLD,
            "p_min_margin": tag_config.TAG_MIN_MARGIN,
        }) or []
        row = result[0] if isinstance(result, list) and result else result
        row = row or {}
        totals["courses"] += 1
        for key in totals:
            if key != "courses":
                totals[key] += int(row.get(key) or 0)
        logger.info("tag_recompute course_id=%s tagged=%s below_threshold=%s ambiguous=%s changed=%s gap_filled=%s",
                    course["id"], row.get("tagged", 0), row.get("below_threshold", 0),
                    row.get("ambiguous", 0), row.get("changed", 0), row.get("gap_filled", 0))
    return totals
