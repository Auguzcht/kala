"""Async worker (Lambda), triggered by EventBridge Scheduler. Not in the
request path. Each scheduled run does six best-effort things, all tenant-scoped and
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
  4. readiness_snapshot — write one readiness_snapshots row per active
     student per run, so the twin has an actual history, not just a
     current state.
  5. item_generation — drain at most two queued diagnostic/practice item
     generations in the worker's bounded long-model slice.
  6. tag_backfill — tag any content_items chunk stored + embedded but not yet
     classified against the course's approved skills. This moved OUT of the
     /ingest HTTP endpoint (services/api): tagging is one reasoning-model call
     per chunk, measured 3-150s each, which does not belong on the api
     Lambda's 30s wall. It is skipped when item_generation claims the
     long-model slot.

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

import json
import logging
import time
from datetime import UTC, datetime

from app.bank_config import CHAIN_MAX
from app.config import get_settings
from app.db import supabase as db
from app.jobs import (
    bank_build,
    embed_backfill,
    ingest_walk,
    item_generation,
    readiness_snapshot,
    reconcile_mastery,
    tag_backfill,
)

logger = logging.getLogger("kala.worker")
logger.setLevel(logging.INFO)

# Matches the worker Lambda timeout in infra/terraform/lambda.tf.
_INVOCATION_BUDGET_SECONDS = 120.0


def _long_job_work() -> tuple[bool, bool]:
    """Return tag/bank pending flags; fail open to the legacy tag path."""
    try:
        tag_work = bool(db.select("content_items", {"tag_attempted_at": "is.null", "chunk_text": "not.is.null", "select": "id", "limit": "1"}))
        bank_work = bool(db.select("skill_bank_state", {"status": "in.(waiting_content,building,error)", "select": "skill_id", "limit": "1"}))
        return tag_work, bank_work
    except Exception as exc:  # noqa: BLE001
        logger.info("long-job work probe unavailable; preserving tag path error=%s", type(exc).__name__)
        return True, False


def _last_long_job() -> str | None:
    try:
        value = (db.select("worker_state", {"key": "eq.long_job_last", "select": "value", "limit": "1"}) or [{}])[0].get("value") or {}
        return value.get("job")
    except Exception as exc:  # noqa: BLE001
        logger.info("worker-state probe unavailable error=%s", type(exc).__name__)
        return None


def _record_long_job(name: str) -> None:
    try:
        db.upsert("worker_state", [{"key": "long_job_last", "value": {"job": name}, "updated_at": datetime.now(UTC).isoformat()}], on_conflict="key")
    except Exception as exc:  # noqa: BLE001
        logger.info("worker-state update unavailable error=%s", type(exc).__name__)


def handler(event, context):
    invocation_started = time.monotonic()
    event = event or {}
    institution_id = (event.get("scope") or {}).get("institution_id")
    targeted_course_id = event.get("courseId")
    trigger = event.get("trigger")
    chain_depth = int(event.get("chainDepth", 0) or 0)

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    def run_one(name, job) -> None:
        """Run one isolated job and record structured timing/result."""
        started = time.monotonic()
        logger.info("job start name=%s institution_id=%s", name, institution_id or "all")
        try:
            job_kwargs = {"institution_id": institution_id}
            if targeted_course_id and name == "bankBuild":
                job_kwargs["course_id"] = targeted_course_id
                job_kwargs["chain_depth"] = chain_depth
            if name == "itemGeneration":
                job_kwargs["remaining_seconds"] = max(
                    0.0,
                    _INVOCATION_BUDGET_SECONDS - (time.monotonic() - invocation_started),
                )
            result = job.run(**job_kwargs)
            results[name] = result
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.info(
                "job done name=%s duration_ms=%d result=%s", name, duration_ms, result,
            )
        except Exception as exc:  # noqa: BLE001 — surface loudly; don't crash the whole run
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.error(
                "job failed name=%s duration_ms=%d error=%s", name, duration_ms, exc,
            )
            errors[name] = str(exc)

    if targeted_course_id and trigger:
        if trigger == "skills_approved":
            db.update("content_items", {"course_id": f"eq.{targeted_course_id}", "skill_id": "is.null"}, {"tag_attempted_at": None})
        run_one("bankBuild", bank_build)
        _maybe_chain(targeted_course_id, results.get("bankBuild", {}), chain_depth, errors)
        return {"ok": not errors, "results": results, "errors": errors}

    # Each job runs independently. Dependency order: ingest before embed
    # because embedding reads chunks the walk may have stored; embed before
    # item generation because item RAG reads embeddings; readiness is cheap and
    # should not be lost to a long model slice. Item generation owns the
    # long-model slot before tag.
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("ingestWalk", ingest_walk),
        ("embedBackfill", embed_backfill),
        ("readinessSnapshot", readiness_snapshot),
    ):
        run_one(name, job)

    run_one("itemGeneration", item_generation)
    item_active = bool(results.get("itemGeneration", {}).get("claimed", 0))
    if item_active:
        results["tagBackfill"] = {"skipped": "item_generation_active"}
        logger.info("job skipped name=tagBackfill reason=item_generation_active institution_id=%s", institution_id or "all")
    else:
        tag_work, bank_work = _long_job_work()
        last = _last_long_job()
        if tag_work and bank_work and last == "tagBackfill":
            run_one("bankBuild", bank_build)
            _record_long_job("bankBuild")
            results["tagBackfill"] = {"skipped": "alternated_to_bankBuild"}
        elif tag_work and bank_work:
            run_one("tagBackfill", tag_backfill)
            _record_long_job("tagBackfill")
            results["bankBuild"] = {"skipped": "alternated_to_tagBackfill"}
        elif bank_work:
            run_one("bankBuild", bank_build)
        elif tag_work:
            run_one("tagBackfill", tag_backfill)
        else:
            results["bankBuild"] = {"skipped": "no_work"}
            results["tagBackfill"] = {"skipped": "no_work"}

    return {"ok": not errors, "results": results, "errors": errors}


def _maybe_chain(course_id: str, result: dict, chain_depth: int, errors: dict) -> None:
    if not result.get("remaining") or result.get("rate_limited") or errors.get("bankBuild"):
        return
    if chain_depth >= CHAIN_MAX:
        logger.warning("bank chain stopped course_id=%s reason=chain_max depth=%d", course_id, chain_depth)
        return
    arn = get_settings().worker_function_arn
    if not arn:
        logger.warning("bank chain skipped course_id=%s reason=missing_worker_function_arn", course_id)
        return
    try:
        import boto3
        boto3.client("lambda").invoke(FunctionName=arn, InvocationType="Event",
                                       Payload=json.dumps({"trigger": "bank", "courseId": course_id, "chainDepth": chain_depth + 1}).encode())
    except Exception as exc:  # noqa: BLE001
        logger.warning("bank chain invoke failed course_id=%s error=%s", course_id, exc)
