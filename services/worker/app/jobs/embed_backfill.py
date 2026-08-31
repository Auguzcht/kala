"""Embedding backfill: fill any content_items row with embedding is null.

This is the documented failure mode in docs/UI_AND_MODULES.md section 4 —
ingest_course() already treats a failed embedding call as best-effort (a
flaky free-tier endpoint or a single timeout shouldn't 502 the whole
ingest run), which is the right call for the request path, but it means a
chunk that failed once stays unembedded forever unless something comes
back for it. match_content_items (migration 0004_rag.sql) filters on
"embedding is not null", so an unembedded chunk simply never surfaces in
RAG retrieval — a silent, permanent quality loss for that chunk, not a
crash. This job is that "something."

Same per-chunk failure isolation as the ingest path: one chunk's embedding
call failing must not stop the batch.
"""
from __future__ import annotations

import logging

from app.db import supabase as db
from app.embed import embed

logger = logging.getLogger("kala.worker")

_BATCH_LIMIT = 200  # generous per run; a scheduled job doesn't need to clear
                     # a large backlog in one pass, and this bounds worst-case
                     # Lambda wall-clock time if the backlog is large.


def run(*, institution_id: str | None = None) -> dict:
    filters = {
        "embedding": "is.null",
        "chunk_text": "not.is.null",
        "select": "id,chunk_text",
        "limit": str(_BATCH_LIMIT),
    }
    if institution_id:
        filters["institution_id"] = f"eq.{institution_id}"
    rows = db.select("content_items", filters)

    embedded = 0
    failed = 0
    for row in rows:
        text = row.get("chunk_text")
        if not text:
            continue
        try:
            vector = embed(text)
            if len(vector) != 1024:
                raise ValueError(f"embedding dimension was {len(vector)}, expected 1024")
        except Exception as exc:
            logger.warning("embed backfill: chunk %s failed: %s", row["id"], exc)
            failed += 1
            continue
        db.update("content_items", {"id": f"eq.{row['id']}"}, {"embedding": vector})
        embedded += 1

    return {"attempted": len(rows), "embedded": embedded, "failed": failed}
