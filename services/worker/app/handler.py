"""Async worker (Lambda), triggered by EventBridge Scheduler. Not in the
request path. Each scheduled run does three things, all tenant-scoped and
idempotent, all safe to retry:

  1. reconcile_mastery — replay evidence_events and rebuild mastery_state,
     so "derived, recomputable from the append-only log" is actually true
     rather than only true of the live request path.
  2. embed_backfill — fill any content_items row a flaky embedding call
     left behind, so RAG retrieval quality doesn't silently degrade over
     time (see docs/UI_AND_MODULES.md section 4 for the failure this
     repairs).
  3. readiness_snapshot — write one readiness_snapshots row per active
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
being asked. So app/config.py, app/db/supabase.py, and app/embed.py here
are deliberate, commented duplicates of their services/api equivalents,
trimmed to only what the worker's three jobs need. If either api-side
source changes (the tracer's _K constant, the embedding provider dispatch,
the input_type mapping), grep both trees for the symbol before assuming
one edit is enough.

event["scope"] (optional): pass {"institution_id": "<uuid>"} to run all
three jobs against a single institution instead of every institution, e.g.
for a manual Lambda console invoke against just the demo institution during
rehearsal rather than waiting for the schedule.
"""
from __future__ import annotations

import logging
import time

from app.jobs import embed_backfill, readiness_snapshot, reconcile_mastery

logger = logging.getLogger("kala.worker")
logger.setLevel(logging.INFO)


def handler(event, context):
    event = event or {}
    institution_id = (event.get("scope") or {}).get("institution_id")

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    # Each job runs independently and its own failure doesn't block the
    # others — a Bedrock/embedding outage stopping reconcile_mastery (which
    # has no model dependency at all) would be a needless coupling.
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("embedBackfill", embed_backfill),
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
