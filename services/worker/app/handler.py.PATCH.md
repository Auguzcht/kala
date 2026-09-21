# services/worker/app/handler.py — register the ingest_walk job

Two small edits. The handler already runs each job independently with failure
isolation and per-job timing logs; ingest_walk slots into that list.

### 1. Import it

Change the import line:

```python
from app.jobs import embed_backfill, readiness_snapshot, reconcile_mastery, tag_backfill
```

to:

```python
from app.jobs import (
    embed_backfill, ingest_walk, readiness_snapshot, reconcile_mastery, tag_backfill,
)
```

### 2. Add it to the job tuple — FIRST, before embed

Ordering matters and the existing comment already explains the principle:
"embed before tag, because tagging reads chunks that embedding may have just
backfilled." Extend that chain one link to the left: **ingest_walk before
embed**, because embedding reads chunks that the walk may have just stored.

Change:

```python
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("embedBackfill", embed_backfill),
        ("tagBackfill", tag_backfill),
        ("readinessSnapshot", readiness_snapshot),
    ):
```

to:

```python
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("ingestWalk", ingest_walk),
        ("embedBackfill", embed_backfill),
        ("tagBackfill", tag_backfill),
        ("readinessSnapshot", readiness_snapshot),
    ):
```

The full pipeline now flows on one schedule with no human at a terminal:
**walk stores chunks -> embed fills their vectors -> tag classifies them ->
readiness snapshots the result.** A new course, once its ingest job is
enqueued, ingests itself over the following scheduled runs. That is the whole
point of the change — the request path never does unbounded LMS work again.
