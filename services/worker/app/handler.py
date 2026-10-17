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
  6. tag_recompute — classify every embedded chunk against approved skill
     embeddings in one database operation per course. It makes no model calls.

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

from app import skill_proposer
from app.bank_config import CHAIN_MAX
from app.config import get_settings
from app.db import supabase as db
from app.jobs import (
    assign_lesson_checks,
    bank_build,
    embed_backfill,
    embed_bank_items,
    ingest_walk,
    item_generation,
    readiness_snapshot,
    reconcile_mastery,
    tag_recompute,
)

logger = logging.getLogger("kala.worker")
logger.setLevel(logging.INFO)

# Matches the worker Lambda timeout in infra/terraform/lambda.tf.
_INVOCATION_BUDGET_SECONDS = 120.0


def handler(event, context):
    invocation_started = time.monotonic()
    event = event or {}
    institution_id = (event.get("scope") or {}).get("institution_id")
    targeted_course_id = event.get("courseId")
    trigger = event.get("trigger")
    chain_depth = int(event.get("chainDepth", 0) or 0)

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    def run_one(name, job, course_id_override: str | None = None, extra: dict | None = None) -> dict:
        """Run one isolated job and record structured timing/result."""
        started = time.monotonic()
        logger.info("job start name=%s institution_id=%s", name, institution_id or "all")
        try:
            job_kwargs = {"institution_id": institution_id}
            job_kwargs.update(extra or {})
            job_course_id = targeted_course_id or course_id_override
            if job_course_id and name in {"bankBuild", "tagRecompute", "skillProposer"}:
                job_kwargs["course_id"] = job_course_id
                if name == "bankBuild":
                    job_kwargs["chain_depth"] = chain_depth
            if name == "itemGeneration":
                job_kwargs["remaining_seconds"] = max(
                    0.0,
                    _INVOCATION_BUDGET_SECONDS - (time.monotonic() - invocation_started),
                )
            if name == "skillProposer":
                job_kwargs["remaining_seconds"] = max(
                    0.0,
                    _INVOCATION_BUDGET_SECONDS - (time.monotonic() - invocation_started),
                )
            if name == "bankBuild" and not (targeted_course_id and trigger):
                # Scheduled resumes share the Lambda wall clock with every
                # other job. Pass a positive remainder so bank_build keeps its
                # own deadline instead of falling back to the full 100s slice.
                job_kwargs["remaining_seconds"] = max(
                    1.0,
                    _INVOCATION_BUDGET_SECONDS - (time.monotonic() - invocation_started),
                )
            result = job.run(**job_kwargs)
            results[name] = result
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.info(
                "job done name=%s duration_ms=%d result=%s", name, duration_ms, result,
            )
            return result
        except Exception as exc:  # noqa: BLE001 — surface loudly; don't crash the whole run
            duration_ms = round((time.monotonic() - started) * 1000)
            logger.error(
                "job failed name=%s duration_ms=%d error=%s", name, duration_ms, exc,
            )
            errors[name] = str(exc)
            return {}

    if targeted_course_id and trigger:
        if trigger == "lesson_checks":
            lesson_id = event.get("lessonId")
            if lesson_id:
                run_one("assignLessonChecks", assign_lesson_checks, extra={"lesson_id": lesson_id})
            return {"ok": not errors, "results": results, "errors": errors}
        if trigger in {"skills_approved", "skills_changed"}:
            run_one("tagRecompute", tag_recompute)
        if trigger == "propose":
            run_one("skillProposer", skill_proposer)
            _maybe_chain(targeted_course_id, results.get("skillProposer", {}), chain_depth, errors, trigger)
        else:
            run_one("bankBuild", bank_build)
            _maybe_chain(targeted_course_id, results.get("bankBuild", {}), chain_depth, errors, "bank")
        return {"ok": not errors, "results": results, "errors": errors}

    # Each job runs independently. Dependency order: ingest before embed
    # because embedding reads chunks the walk may have stored; embed before
    # item generation because item RAG reads embeddings; readiness is cheap and
    # should not be lost to a long model slice.
    for name, job in (
        ("reconcileMastery", reconcile_mastery),
        ("ingestWalk", ingest_walk),
        ("embedBackfill", embed_backfill),
        ("embedBankItems", embed_bank_items),
        ("readinessSnapshot", readiness_snapshot),
    ):
        run_one(name, job)

    run_one("itemGeneration", item_generation)
    run_one("tagRecompute", tag_recompute)

    # A Refresh can hit its bounded async chain limit with a durable partial
    # window cursor. Resume those courses on the next scheduled worker run.
    for course_id in _incomplete_proposal_courses():
        remaining_seconds = max(
            0.0,
            _INVOCATION_BUDGET_SECONDS - (time.monotonic() - invocation_started),
        )
        if remaining_seconds < 50.0:
            logger.info("skillProposer scheduled resume deferred course_id=%s reason=budget", course_id)
            continue
        result = run_one("skillProposer", skill_proposer, course_id)
        _maybe_chain(course_id, result, chain_depth, errors, "propose")

    run_one("bankBuild", bank_build)

    return {"ok": not errors, "results": results, "errors": errors}


def _incomplete_proposal_courses() -> list[str]:
    try:
        rows = db.select("worker_state", {
            "key": "like.proposer:%", "select": "key,value", "limit": "10000",
        })
    except Exception as exc:  # noqa: BLE001 — other scheduled jobs still run
        logger.warning("proposer resume scan failed error=%s", exc)
        return []
    course_ids = set()
    for row in rows:
        key = row.get("key") or ""
        parts = key.split(":", 2)
        if len(parts) != 3 or parts[0] != "proposer":
            continue
        value = row.get("value") or {}
        completed = int(value.get("windows_completed") or 0)
        total = value.get("windows_total")
        if total is None or completed < int(total):
            course_ids.add(parts[1])
    return sorted(course_ids)


def _maybe_chain(course_id: str, result: dict, chain_depth: int, errors: dict, trigger: str = "bank") -> None:
    job_name = "skillProposer" if trigger == "propose" else "bankBuild"
    if result.get("permanent_error"):
        logger.error("%s chain stopped course_id=%s reason=permanent_error status=%s detail=%s",
                     job_name, course_id, result.get("error_status"), result.get("error_reason"))
        return
    if result.get("rate_limited"):
        logger.warning("%s chain stopped course_id=%s reason=throttle", job_name, course_id)
        return
    if result.get("stop_reason") == "permanent_error":
        logger.error("%s chain stopped course_id=%s reason=permanent_error status=%s detail=%s",
                     job_name, course_id, result.get("error_status"), result.get("error_reason"))
        return
    if result.get("retry_deferred"):
        logger.info("%s chain stopped course_id=%s reason=transient_backoff", job_name, course_id)
        return
    if errors.get(job_name):
        logger.error("%s chain stopped course_id=%s reason=permanent_error detail=%s",
                     job_name, course_id, errors[job_name])
        return
    if not result.get("remaining"):
        logger.info("%s chain stopped course_id=%s reason=done", job_name, course_id)
        return
    if chain_depth >= CHAIN_MAX:
        logger.warning("%s chain stopped course_id=%s reason=depth_limit depth=%d "
                       "handing off to schedule remaining=%s",
                       job_name, course_id, chain_depth,
                       result.get("modulesRemaining", result.get("remaining")))
        return
    if result.get("budget_exhausted"):
        logger.info("%s continuation course_id=%s reason=budget depth=%d", job_name, course_id, chain_depth)
    arn = get_settings().worker_function_arn
    if not arn:
        logger.warning("%s chain stopped course_id=%s reason=budget missing_worker_function_arn",
                       job_name, course_id)
        return
    try:
        import boto3
        boto3.client("lambda").invoke(FunctionName=arn, InvocationType="Event",
                                       Payload=json.dumps({"trigger": trigger, "courseId": course_id, "chainDepth": chain_depth + 1}).encode())
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s chain stopped course_id=%s reason=budget invoke_error=%s", job_name, course_id, exc)
