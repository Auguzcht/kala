"""Worker-side RAG retrieval for async item generation.

Deliberate trimmed duplicate of services/api/app/ai/rag.py. The worker image
only copies its own app/ tree, so it cannot import the API's RAG module. Keep
the embedding input type, RPC name, tenant/course arguments, and default k in
sync with the API copy; grep both files for `match_content_items` before
changing either one.
"""
from __future__ import annotations

from app import embed
from app.db import supabase as db


def retrieve(*, institution_id: str, course_id: str, query: str, k: int = 5) -> list[dict]:
    query_embedding = embed.embed(query, input_type="search_query")
    return db.rpc("match_content_items", {
        "p_institution_id": institution_id,
        "p_course_id": course_id,
        "p_query": query_embedding,
        "p_match_count": k,
    }) or []
