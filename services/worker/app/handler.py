"""Async worker (Lambda), triggered by EventBridge Scheduler. Not in the
request path. Each scheduled run does five things, all tenant-scoped and
idempotent, all safe to retry:

  1. reconcile_mastery — replay evidence_events and rebuild mastery_state,
     so "derived, recomputable from the append-only log" is actually true
     rather than only true of the live request path.
  2. ingest_walk — advance any enqueued course ingest by one bounded
     frontier slice: fetch a folder's children, store new content rows,
     checkpoint. This moved OUT of the /ingest HTTP endpoint (services/api):
     the whole-tree walk measured 31.8s on a real course, over the api
     Lambda's 30s wall before a single PDF, so ingest silently timed out.
     /ingest now writes an ingest_jobs row and returns 202; this job drains
     it over successive scheduled runs, no manual re-POSTing. See
     docs/design/async-ingest.md.
  3. embed_backfill — fill any content_items row a flaky embedding call
     left behind, so RAG retrieval quality doesn't silently degrade over
     time (see docs/UI_AND_MODULES.md section 4 for the failure this
     repairs).
  4. tag_backfill — tag any content_items chunk stored + embedded but not
     yet classified against the course's approved skills. This moved OUT of
     the /ingest HTTP endpoint (services/api): tagging is one reasoning-model
     call per chunk, measured 3-150s each, which does not belong on the api
     Lambda's 30s wall. Here it runs on the worker's 120s ceiling and drains
     a course's backlog over successive scheduled runs, no manual re-POSTing.
  5. readiness_snapshot — write one readiness_snapshots row per active
     student per run, so the twin has an actual history, not just a
     current state.

Deliberately NOT in this worker: LMS grade/attempt sync. That would need a
get_attempts()-shaped method the LMSConnector protocol (app/lms/base.py)
doesn't define yet, real submissions in a real gradebook column to sync
against, and it produces nothing visible in the product. Scoped out for
September 1, not silently dropped — see the standing constraint at the top
of the root CLAUDE.md before adding it (no infra change without asking).

Why this file duplicates services/api code instead of importing it
--------------------------------------------------------------------
services/worker/Dockerfile only `COPY app ./app` — it has no access to
services/api's source tree at build time, and the two are already built,
pushed, and deployed as separate container images (see Makefile's `build`
target and infra/terraform/lambda.tf's two separate aws_lambda_function
resources). Making them share code would mean moving the shared modules
into packages/ and changing both Dockerfiles' COPY lines — an infra-shaped
change the root CLAUDE.md's standing constraint says not to make without
being asked. So app/config.py, app/db/supabase.py, app/embed.py, and
app/tagger.py here are deliberate, commented duplicates of their
services/api equivalents, trimmed to only what the worker's jobs need. If
either api-side source changes (the tracer's _K constant, the embedding
provider dispatch, the input_type mapping, the tag_content prompt/budget),
grep both trees for the symbol before assuming one edit is enough.

event["scope"] (optional): pass {"institution_id": "<uuid>"} to run all
jobs against a single institution instead of every institution, e.g.
for a manual Lambda console invoke against just the demo institution during
rehearsal rather than waiting for the schedule.
"""
from __future__ import annotations

import logging
import time

from app.jobs import (
    embed_backfill, ingest_walk, readiness_snapshot, reconcile_mastery, tag_backfill,
)

logger = logging.getLogger("kala.worker")
logger.setLevel(logging.INFO)


def handler(event, context):
    event = event or {}
    institution_id = (event.get("scope") or {}).get("institution_id")

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    # Each job runs independently and its own failure doesn't block the
    # others — a Bedrock/embedding outage stopping reconcile_mastery (which
    # has no model dependency at all) would be a needless coupling. Order:
    # ingest_walk before embed, because embedding reads chunks that the walk
    # may have just stored; embed before tag, because tagging reads chunks
    # that embedding may have just backfilled; all five are best-effort and
    # a miss is picked up next run.
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("ingestWalk", ingest_walk),
        ("embedBackfill", embed_backfill),
        ("tagBackfill", tag_backfill),
        ("readinessSnapshot", readiness_snapshot),
    ):
        started = time.monotonic()
        logger.info("job start name=%s institution_id=%s", name, institution_id or "all")
        try:
            result = job.run(institution_id=institution_id)
            results[name] = result
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.info(
                "job done name=%s duration_ms=%d result=%s", name, duration_ms, result,
            )
        except Exception as exc:  # surface loudly in logs; don't crash the whole run
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.error(
                "job failed name=%s duration_ms=%d error=%s", name, duration_ms, exc,
            )
            errors[name] = str(exc)

    return {"ok": not errors, "results": results, "errors": errors}
