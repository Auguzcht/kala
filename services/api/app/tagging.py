"""Synchronous embedding-only course tagging used by staff retagging."""
from __future__ import annotations

import logging

from app import tag_config
from app.db import supabase as db

logger = logging.getLogger(__name__)


def tag_recompute(*, course_id: str, institution_id: str) -> dict:
    approved = db.select("skills", {
        "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{institution_id}",
        "status": "eq.approved",
        "select": "id,name,embedding",
    })
    for skill in approved:
        if skill.get("embedding") is None:
            logger.warning("tag_recompute skill_missing_embedding course_id=%s skill_id=%s name=%s",
                           course_id, skill["id"], skill.get("name"))
    result = db.rpc("recompute_embedding_tags", {
        "p_course_id": course_id,
        "p_threshold": tag_config.TAG_THRESHOLD,
        "p_min_margin": tag_config.TAG_MIN_MARGIN,
    }) or []
    return (result[0] if isinstance(result, list) and result else result) or {
        "tagged": 0, "below_threshold": 0, "ambiguous": 0,
        "changed": 0, "gap_filled": 0,
    }
