"""Resumably embed a bounded batch of active bank items per invocation."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.db import supabase as db
from app.embed import embed

logger = logging.getLogger("kala.worker")
_BATCH_LIMIT = 10


def run(*, institution_id: str | None = None) -> dict:
    filters = {
        "origin": "eq.bank", "kind": "eq.practice", "retired_at": "is.null",
        "embedding": "is.null", "select": "id,prompt", "limit": str(_BATCH_LIMIT),
        "order": "created_at.asc",
    }
    if institution_id:
        filters["institution_id"] = f"eq.{institution_id}"
    rows = db.select("generated_items", filters)
    embedded = failed = 0
    for row in rows:
        try:
            vector = embed(row["prompt"])
            if len(vector) != 1024:
                raise ValueError(f"embedding dimension {len(vector)}, expected 1024")
            db.update("generated_items", {"id": f"eq.{row['id']}", "embedding": "is.null"}, {
                "embedding": vector, "embedded_at": datetime.now(UTC).isoformat(),
            })
            embedded += 1
        except Exception as exc:  # noqa: BLE001 - a single item must not block the batch
            logger.warning("bank item embedding failed item_id=%s error=%s", row["id"], exc)
            failed += 1
    return {"attempted": len(rows), "embedded": embedded, "failed": failed,
            "remaining": len(rows) == _BATCH_LIMIT}
