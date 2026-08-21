"""RAG over course content. Embeds the query and asks Postgres (pgvector) for
the nearest content chunks, scoped to the institution. Requires the
match_content_items function in migration 0004_rag.sql."""
from __future__ import annotations

from app.ai import bedrock
from app.db import supabase as db


def retrieve(*, institution_id: str, course_id: str, query: str, k: int = 5) -> list[dict]:
    query_embedding = bedrock.embed(query, input_type="search_query")
    return db.rpc("match_content_items", {
        "p_institution_id": institution_id,
        "p_course_id": course_id,
        "p_query": query_embedding,
        "p_match_count": k,
    }) or []
