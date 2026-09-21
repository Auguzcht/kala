"""Ingest walk: drain enqueued ingest_jobs by expanding the course content tree
ONE bounded frontier slice per worker run, checkpointing between slices.

WHY THIS EXISTS. The old ingest walked the whole tree inside the api's /ingest
request, on the 30s Lambda wall. A real course (AWS101) measured 31.8s for the
walk ALONE — over the wall before a single PDF, so ingest silently timed out at
30000.00 ms with no "Ingest pulled" log line ever printed. Raising a timeout
just moves the cliff to the next-bigger course. The durable fix is the tagging
fix again: take the batch off the request-response door, and make the DATABASE
the progress record so any killed run resumes.

THE MODEL.
  - The api's POST /ingest no longer walks. It writes one ingest_jobs row
    (status=pending) and returns 202 immediately. (services/api change.)
  - This job, on the worker's schedule, picks up the oldest pending/in_progress
    job and advances it by a BOUNDED slice:
        pop up to _FOLDERS_PER_RUN entries off the job's frontier ONE AT A
        TIME, fetch each folder's children (one REST call each), store new
        content rows, optionally fetch PDF attachments, append newly
        discovered child folders to the frontier, checkpoint AFTER EACH
        FOLDER (not once for the whole slice — see CHECKPOINTING below).
  - Empty frontier after a slice => status=complete. More => in_progress, the
    next scheduled run continues.

RESUMABILITY. The frontier lives in the job row; the content lives in
content_items with the same dedupe-by-lms_ref the api used. A mid-slice kill
loses at most the ONE folder currently being expanded (not expanded at all —
see below), which is simply re-expanded next run — dedupe makes the re-store
a no-op. No cursor to lose.

CHECKPOINTING (fixed — was batched, now per-folder). The original cut of this
job called _checkpoint() once, after the whole slice loop finished. That meant
a BlackboardRateLimitedError partway through a 20-folder slice lost every
already-expanded folder's frontier progress in that slice: the job resumes
next run by re-popping the SAME 20 folders, including the ones already
expanded (safe, but wasted quota re-fetching what we already had) — and if the
quota window is narrower than one slice, this can loop with zero net forward
progress, which is the exact outage this whole effort exists to prevent.

Fixed to checkpoint after EVERY folder, mirroring tag_backfill's per-chunk
checkpoint discipline exactly (see app/jobs/tag_backfill.py: it marks each
chunk done right after processing it, never batched). The frontier is now a
single working queue: pop one folder off the front, expand it, append any
newly discovered child containers to the back, write the frontier back to the
job row, repeat until the run's folder budget is spent or the frontier is
empty. A rate-limit or real error mid-folder puts that one un-expanded folder
back on the front of the frontier before checkpointing/re-raising, so nothing
is lost and nothing is double-counted.

RATE LIMITS. This is the job that could re-create the very outage this whole
effort fixed, so it is deliberately conservative: bounded folders per run,
bounded PDFs per run, and a BlackboardRateLimitedError checkpoints what we have
and stops CLEAN — it never loops against an exhausted quota. Concurrency is
intentionally NOT added here in the first pass: correctness and quota-safety
first; a bounded concurrency pool over fetch_children is a later optimization
noted in the brief, gated on the rate-limit headroom being proven.

DEDUPE ON DISCOVERED (fixed — was absent). No container should be queued for
expansion twice within one run: `_queued` tracks every id that has ever been
placed in the frontier this run (whether already expanded or still pending),
so a container reachable as a child of two different parents — or, in a
malformed/cyclic tree, a child of itself further down — is only ever expanded
once per run. This is RUN-LOCAL: it does not persist across runs, so if a
container is discovered again in a LATER run (after this run's in-memory set
is gone) it can be re-queued. Ingest is dedupe-by-lms_ref at the content-row
level regardless, so a re-expansion re-fetches from Blackboard but never
double-stores. Full cross-run cycle-safety would need a persisted seen-set on
the job row (an infra/migration change) — noted as a follow-up, not blocking,
per the brief's "fix defensively, don't block on it."

STATUS: SCAFFOLD. Structure, lifecycle, checkpointing and bounds are complete
and reviewable. The two spots that call the live connector are marked
TODO(verify-live) — DeepSeek runs them against the real instance from the
worker image, exactly as the PDF fetch was verified before, and adds tests
mirroring test_course_sync_cache.py's style.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.chunking import chunk_text, extract_text, resolve_mime_type, strip_pii
from app.db import supabase as db
from app.lms.blackboard import BlackboardRateLimitedError, WorkerBlackboardConnector

logger = logging.getLogger("kala.worker")

# How many folders to expand per worker run. Each is one REST call (~0.8s live).
# 20 * 0.8s = ~16s of network, well inside the worker's 120s ceiling with room
# for stores and PDF fetches. Count-bound, not time-bound: the 120s Lambda
# timeout is the real ceiling and a mid-slice kill just resumes next run.
_FOLDERS_PER_RUN = 20

# How many PDFs to fetch+extract per run, when include_attachments is set.
# ~2s fetch + cheap extract each (measured). Kept low so PDF work never
# dominates a run; the rest drain on following runs, same resumable contract.
_PDFS_PER_RUN = 5

# Process at most this many jobs per worker run, so one course's backlog does
# not starve another institution's pending job. Each job still only advances by
# one bounded slice per run regardless.
_JOBS_PER_RUN = 3

# Fallback wait when a 429 arrives WITHOUT a parsable Retry-After header.
# Blackboard normally sends one (`Retry-After: 20807s`), but the header is
# optional in the spec and the parse can fail — and leaving the job eligible
# in that case would reproduce the exact spin the backoff exists to prevent.
# 15 minutes matches the scheduler's own cadence, so the job is retried on the
# next tick rather than storming, and a genuinely long window still gets the
# real value from the header when it IS present.
_DEFAULT_BACKOFF_SECONDS = 900


def run(*, institution_id: str | None = None) -> dict:
    """Advance up to _JOBS_PER_RUN pending/in_progress ingest jobs by one
    bounded slice each. institution_id None = all institutions (the schedule);
    a value scopes to one (manual console invoke), same contract as the other
    worker jobs.

    Jobs inside a throttle backoff (not_before in the future) are SKIPPED, not
    failed. Without this, a job whose quota window is fully exhausted would be
    re-attempted every 15 minutes forever: 429 on the first call, nothing
    expanded, nothing checkpointed, repeat — zero net progress and no signal
    anywhere. The per-folder checkpoint cannot fix that case, because there is
    no progress to checkpoint.
    """
    pickup_filter = {
        # not_before is the retry-after skip (FIX B). NULL means never
        # throttled, which is why it is eligible; a future value means we are
        # still inside a window Blackboard told us to wait out.
        "not_before": f"is.null,not_before.lte.{_utc_now_iso()}",
        "status": "in.(pending,in_progress)",
        "select": "id,institution_id,course_id,status,frontier,folders_expanded,"
                  "items_stored,pdfs_fetched,include_attachments,seen,not_before",
        "order": "created_at.asc",
        "limit": str(_JOBS_PER_RUN),
    }
    if institution_id:
        pickup_filter["institution_id"] = f"eq.{institution_id}"

    jobs = db.select("ingest_jobs", pickup_filter)
    if not jobs:
        return {"jobsAdvanced": 0}

    connector = WorkerBlackboardConnector()
    advanced = 0
    completed = 0
    rate_limited = 0

    for job in jobs:
        try:
            outcome = _advance_one(connector, job)
            advanced += 1
            if outcome == "complete":
                completed += 1
        except BlackboardRateLimitedError as exc:
            # Do NOT fail the job — this is transient by definition. _advance_one
            # checkpoints after every folder it successfully expands (see module
            # docstring), so by the time this exception reaches us the frontier
            # already reflects every folder actually completed this run; at most
            # the one folder that was mid-fetch when the 429 landed is un-expanded,
            # and it was put back on the frontier before the checkpoint.
            #
            # FIX B: record the retry-after Blackboard just gave us and skip
            # this job until then. Stopping this run is not enough on its own —
            # with the window fully exhausted, the NEXT scheduled run would
            # re-attempt immediately, get 429 on its first call, and repeat
            # forever with zero net progress. The exception carries the exact
            # wait, so use it rather than retrying blind on the schedule.
            #
            # Counted as advanced: the job DID move (frontier checkpointed),
            # just not to completion. Reporting 0 here would read as "nothing
            # happened" in the run log while the job row says otherwise.
            advanced += 1
            rate_limited += 1
            _set_backoff(job["id"], exc.retry_after)
            logger.warning(
                "ingest walk rate-limited job=%s; checkpointed, backoff=%ss: %s",
                job["id"], exc.retry_after, exc,
            )
            break  # whole quota is shared; no point trying the next job either
        except Exception as exc:
            # A real, non-transport failure. _advance_one has already
            # checkpointed every folder it completed before re-raising, so we
            # only need to flip status to failed here. Never machine-retried,
            # mirroring tag_backfill's transport-vs-real distinction.
            #
            # Also counted as advanced for the same reason as the throttle
            # branch: partial work was checkpointed before the failure.
            advanced += 1
            logger.error("ingest walk failed job=%s: %s", job["id"], exc)
            _mark_failed(job["id"], str(exc))

    return {
        "jobsAdvanced": advanced,
        "jobsCompleted": completed,
        "rateLimited": rate_limited,
    }


def _advance_one(connector: WorkerBlackboardConnector, job: dict) -> str:
    """Advance a single job by one bounded slice, checkpointing after EVERY
    folder expanded (not once for the whole slice — see module docstring on
    CHECKPOINTING). Returns 'complete' or 'in_progress'."""
    job_id = job["id"]
    course_id = job["course_id"]
    institution_id = job["institution_id"]
    include_attachments = bool(job.get("include_attachments"))

    # course_ref: the Blackboard-side id this walk hits. The api stores the
    # internal course_id on the job; the walk needs the lms_course_id. Resolve
    # it once from the courses row (local, no Blackboard call).
    course_rows = db.select("courses", {
        "id": f"eq.{course_id}", "select": "lms_course_id", "limit": "1",
    })
    if not course_rows:
        raise RuntimeError(f"course {course_id} not found for ingest job {job_id}")
    course_ref = course_rows[0]["lms_course_id"]

    existing_refs = _existing_refs(institution_id, course_id)

    # FIX A: containers expanded on PREVIOUS runs, loaded from the job row.
    # Defined here, BEFORE the seed branch, because that branch checkpoints too.
    #
    # Tolerant of the column not existing yet (0018 unapplied): job.get returns
    # None and this degrades to the pre-0018 run-local-only behavior rather
    # than raising. Same fail-open direction as course_by_lms_external_id.
    seen: set[str] = set(job.get("seen") or [])

    # Running totals for THIS call, seeded from the job row so a checkpoint at
    # any point writes the correct cumulative total, not just this run's delta.
    folders_expanded_total = job.get("folders_expanded", 0)
    items_stored_total = job.get("items_stored", 0)
    pdfs_fetched_total = job.get("pdfs_fetched", 0)

    # Seed the frontier on first touch: the course's top-level content ids.
    frontier = job.get("frontier")
    if frontier is None:
        # TODO(verify-live): fetch_children(course_ref, None) returns the
        # top-level contents. Seed the frontier with the container ids among
        # them, and store the top-level leaf items right away.
        top = connector.fetch_children(course_ref)
        frontier, seeded_stored = _seed_from_top(
            connector, institution_id, course_id, top, existing_refs,
        )
        items_stored_total += seeded_stored
        _touch_started(job_id)
        # Persist the seed immediately: if the run dies before the slice loop
        # below even starts, we do not want to re-fetch and re-seed the
        # top level again next run (harmless via dedupe, but wasted quota).
        _checkpoint(
            job_id,
            frontier=frontier,
            folders_expanded=folders_expanded_total,
            items_stored=items_stored_total,
            pdfs_fetched=pdfs_fetched_total,
            status="in_progress" if frontier else "complete",
            seen=seen,
        )
        if not frontier:
            return "complete"

    # `_queued` dedupes discovered containers within this run: an id already
    # placed on the frontier (whether already expanded this run or still
    # waiting) is never appended again. See module docstring, DEDUPE ON
    # DISCOVERED. Seeded from the current frontier so top-level containers
    # can't be re-queued if re-discovered as a child further down.
    #
    # The frontier holds (container_id, folder_path) pairs, NOT bare ids. The
    # api's build_folder_paths() needs the whole content list in memory to
    # resolve ancestry, which an incremental walk by definition never has — so
    # each container carries its own ancestor chain down instead. This is what
    # lets _store_item write a real folder_path/module_ref rather than the
    # empty ones a bare-id frontier would silently produce.
    frontier = _normalize_frontier(frontier)
    # Anything sitting on the frontier is by definition already queued, and
    # anything in `seen` was expanded on an earlier run. The union is what the
    # discovery check below tests against.
    queued = {cid for cid, _p, _t in frontier} | seen

    expanded_this_run = 0
    pdfs_this_run = 0
    status = "in_progress"

    while frontier and expanded_this_run < _FOLDERS_PER_RUN:
        folder_id, folder_path, folder_title = frontier.pop(0)
        # folder_path is THIS folder's own ancestry; its children's path is
        # derived below, once, for all of them.
        try:
            # TODO(verify-live): one REST call per folder.
            children = connector.fetch_children(course_ref, folder_id)
        except Exception:
            # Nothing was expanded for this folder — put it back at the front
            # so next run retries it first, checkpoint what we DID complete
            # this run, then propagate. This is what makes a 429 (or any
            # other failure) mid-slice lose at most the current folder,
            # never the whole slice.
            frontier.insert(0, (folder_id, folder_path, folder_title))
            _checkpoint(
                job_id,
                frontier=frontier,
                folders_expanded=folders_expanded_total,
                items_stored=items_stored_total,
                pdfs_fetched=pdfs_fetched_total,
                status="in_progress",
                seen=seen,
            )
            raise

        # The path for THIS FOLDER's children, computed once for all of them.
        # Every child of this folder — leaf or container — sits one level below
        # it, so they all share the same ancestry: this folder's path plus this
        # folder itself. Computing it per-child-type instead was a real bug:
        # only CONTAINER children got the extended path, so a LEAF child was
        # stored with its PARENT's path and landed with a module_ref one level
        # too shallow (or None at the top). Silent, and exactly the kind of
        # wrong-but-plausible metadata that reads as "the course has no
        # modules" rather than an error.
        children_path = folder_path + [
            {"lmsRef": folder_id, "title": folder_title or folder_id}
        ]

        stored_this_folder = 0
        for raw in children:
            item = connector.flatten_item(raw)
            cid = item.get("lms_content_id")
            if not cid:
                continue
            if connector.is_container(raw) and cid not in queued:
                # A container's own children will be one level deeper still,
                # so it is queued WITH children_path; when expanded, that
                # becomes the base its children extend.
                frontier.append((cid, children_path, item.get("title") or cid))
                queued.add(cid)
            stored_this_folder += _store_item(
                institution_id, course_id, item, existing_refs,
                folder_path=children_path,
                module_ref=module_ref_for(children_path),
            )
            if include_attachments and pdfs_this_run < _PDFS_PER_RUN:
                pdfs_this_run += _fetch_pdfs(
                    connector, institution_id, course_id, raw, item,
                    existing_refs, budget=_PDFS_PER_RUN - pdfs_this_run,
                    folder_path=children_path,
                    module_ref=module_ref_for(children_path),
                )

        expanded_this_run += 1
        folders_expanded_total += 1
        items_stored_total += stored_this_folder
        # pdfs_this_run is cumulative across folders in this run (the budget
        # check above is against the running total), so the job-row total is
        # just the job's baseline plus that running figure, recomputed fresh
        # each checkpoint rather than incremented twice.
        pdfs_fetched_total = job.get("pdfs_fetched", 0) + pdfs_this_run

        seen.add(folder_id)
        status = "complete" if not frontier else "in_progress"
        _checkpoint(
            job_id,
            frontier=frontier,
            folders_expanded=folders_expanded_total,
            items_stored=items_stored_total,
            pdfs_fetched=pdfs_fetched_total,
            status=status,
            seen=seen,
        )
        logger.info(
            "ingest walk job=%s expanded folder=%s stored=%d pdfs_run=%d "
            "remaining=%d status=%s",
            job_id, folder_id, stored_this_folder, pdfs_this_run,
            len(frontier), status,
        )

    return status


def _seed_from_top(connector, institution_id, course_id, top, existing_refs) -> tuple[list, int]:
    """Store top-level leaf items and return (initial frontier, items stored).

    The frontier is (container_id, folder_path, title) TRIPLES. Top-level
    containers get an empty path — they are the roots, matching the api's
    build_folder_paths() which gives top-level content an empty list. That
    means a top-level container's own body gets module_ref=None, and its
    CHILDREN get a one-entry path naming it. Same result the api's whole-tree
    walk produces, arrived at incrementally.

    `connector` is the injected walk connector, NOT the class. Reaching for
    WorkerBlackboardConnector.flatten_item directly worked in production but
    made this function untestable and un-substitutable (a fake connector was
    silently bypassed for these two calls). Everything else in this module
    already takes the connector; this now matches.

    Fixed: previously returned only the container list and discarded the
    store count, so every seed-time store was invisible to items_stored.
    """
    containers: list[tuple[str, list, str]] = []
    stored = 0
    for raw in top:
        item = connector.flatten_item(raw)
        cid = item.get("lms_content_id")
        if not cid:
            continue
        if connector.is_container(raw):
            containers.append((cid, [], item.get("title") or cid))
        stored += _store_item(
            institution_id, course_id, item, existing_refs,
            folder_path=[], module_ref=None,
        )
    return containers, stored


def module_ref_for(folder_path: list) -> str | None:
    """Convenience default: the top-level ancestor's title, or None for content
    at the course root. Duplicate of api lms/hierarchy.module_ref_for — keep in
    sync, since a skill's module_ref grouping is derived from whichever value
    got stored.
    """
    return folder_path[0]["title"] if folder_path else None


def _normalize_frontier(frontier: list) -> list[tuple[str, list, str]]:
    """Accept either shape a frontier may arrive in and return pairs.

    A frontier persisted BEFORE this change (or seeded by an older worker run)
    is a list of bare id strings. A job mid-drain when the worker is redeployed
    would otherwise crash on `for cid, path in frontier`. Bare ids get an empty
    path — the honest answer, since that run never recorded their ancestry, and
    their content is already stored (dedupe skips it) so only their CHILDREN's
    paths are affected.
    """
    out: list[tuple[str, list, str]] = []
    for entry in frontier or []:
        if isinstance(entry, (list, tuple)) and len(entry) == 3:
            cid, path, title = entry
            out.append((cid, path or [], title or cid))
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            cid, path = entry
            out.append((cid, path or [], cid))
        elif isinstance(entry, str):
            out.append((entry, [], entry))
    return out


def _existing_refs(institution_id: str, course_id: str) -> set[str]:
    """lms_refs already stored for this course. One query, same dedupe the api
    used so a resumed walk never double-stores."""
    rows = db.select("content_items", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "lms_ref": "not.is.null",
        "select": "lms_ref",
    })
    return {r["lms_ref"] for r in rows if r.get("lms_ref")}


def _store_item(institution_id, course_id, item, existing_refs, *, folder_path, module_ref) -> int:
    """Store one content item's chunks if not already stored. Returns count of
    chunks stored (0 if skipped or bodyless).

    Chunking + PII stripping match the api's ingest path (see app/chunking.py,
    a deliberate duplicate). One chunk per MAX_CHUNK_CHARS with CHUNK_OVERLAP,
    NOT one chunk per item: a 4000-char module page stored whole becomes a
    single embedding, so retrieval can only ever return "that entire page" as
    a hit. That is the coarse-grain problem the api side already solved, and
    letting it reach a live drain would be invisible — the drain would report
    success, and a later question-bank reset would regenerate questions off
    those same thin chunks.

    `folder_path` / `module_ref` come from the CALLER, not from a tree walk:
    the api's build_folder_paths() needs the whole content list in memory,
    which an incremental walk never has. Instead the frontier carries each
    container's ancestry down with it (see _advance_one), so path information
    is available at store time for exactly the items being stored. Omitting
    these would NOT error — folder_path is `not null default '[]'` — it would
    silently write empty paths, which is the shallow-walk-with-no-error shape
    this codebase has already been burned by.
    """
    body = (item.get("body_or_description") or "").strip()
    if not body:
        return 0
    if item.get("lms_content_id") in existing_refs:
        return 0

    rows = []
    for chunk in chunk_text(body):
        clean = strip_pii(chunk)
        if not clean.strip():
            continue
        rows.append({
            "institution_id": institution_id,
            "course_id": course_id,
            "lms_ref": item.get("lms_content_id"),
            "parent_lms_ref": item.get("parent_id"),
            "folder_path": folder_path,
            "module_ref": module_ref,
            "chunk_text": clean,
        })
    if not rows:
        return 0
    db.insert("content_items", rows)
    # Marked stored even before the next run: dedupe is by lms_ref, and one
    # item now contributes MANY rows sharing that ref. Recording it here keeps
    # a re-encounter within this run from re-storing the whole set.
    existing_refs.add(item.get("lms_content_id"))
    return len(rows)


def _fetch_pdfs(connector, institution_id, course_id, raw, item, existing_refs, *,
                budget, folder_path, module_ref) -> int:
    """Lead B PDF fetch, bounded by budget. Per-PDF failure isolation: one bad
    href must not stop the slice.

    Extracts text, chunks it, strips PII, and stores it as content_items under
    its own lms_ref — the same pipeline /content/upload uses, so a PDF's text
    is retrievable exactly like any other course content rather than being
    fetched and thrown away.

    A permanently broken href never stores, so it is re-attempted on later runs
    and keeps costing one `budget` slot each time — an accepted first-pass
    limitation, same as the api-side note in get_content.
    """
    attachments = connector.extract_pdf_attachments(raw)
    fetched = 0
    for att in attachments:
        if fetched >= budget:
            break
        ref = f"{item.get('lms_content_id')}::{att.get('fileName')}"
        if ref in existing_refs:
            continue
        try:
            data = connector.download(att["href"])
            mime = resolve_mime_type(att.get("fileName") or "", att.get("mimeType"))
            text = extract_text(data, mime)
        except BlackboardRateLimitedError:
            # MUST propagate, NOT be swallowed by the generic handler below.
            # A 429 is the whole quota being gone, not one bad file — the walk
            # has to checkpoint and stop (run() then leaves the job in_progress
            # and skips it until not_before), instead of continuing to spend
            # requests against an exhausted quota. This is the specific reason
            # download() calls _check_rate_limit: without it a throttled PDF
            # fetch arrived here as a plain HTTPStatusError and was silently
            # treated as "this one file failed".
            raise
        except Exception as exc:
            # One unreadable attachment must not lose the rest of the slice.
            # Note this leaves the href un-stored, so a permanently broken one
            # is retried (and consumes a slot) every run — see the docstring.
            logger.warning("PDF fetch failed item=%s: %s", item.get("lms_content_id"), exc)
            continue

        rows = []
        for chunk in chunk_text(text):
            clean = strip_pii(chunk)
            if not clean.strip():
                continue
            rows.append({
                "institution_id": institution_id,
                "course_id": course_id,
                # Its OWN ref: a PDF is course material in its own right, not a
                # suffix on the page that linked it. `:{filename}` keeps it
                # stable across runs so dedupe skips an already-stored file.
                "lms_ref": ref,
                "parent_lms_ref": item.get("lms_content_id"),
                "folder_path": folder_path,
                "module_ref": module_ref,
                "chunk_text": clean,
            })
        if rows:
            db.insert("content_items", rows)
            existing_refs.add(ref)
            fetched += 1
        else:
            # Extracted to nothing (a scanned PDF, an empty document). Nothing
            # to store, but mark it so it does not burn a slot every run — the
            # opposite of the broken-href case, where leaving it unmarked is
            # what allows the retry.
            existing_refs.add(ref)
    return fetched


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _set_backoff(job_id: str, retry_after: int | None) -> None:
    """Record a throttle backoff on the job (FIX B).

    `not_before` = now + retry_after, so run()'s pickup skips this job until
    the window Blackboard named has passed. When retry_after is None (a 429
    with no parsable header), fall back to a fixed conservative wait rather
    than leaving the job immediately eligible — leaving it eligible would
    reproduce exactly the spin this exists to stop.

    Best-effort: failing to record a backoff must not mask the throttle
    itself, which is already logged and already checkpointed.
    """
    wait_seconds = retry_after if retry_after is not None else _DEFAULT_BACKOFF_SECONDS
    try:
        db.update("ingest_jobs", {"id": f"eq.{job_id}"}, {
            "not_before": (_utc_now() + timedelta(seconds=wait_seconds)).isoformat(),
            "updated_at": _utc_now_iso(),
        })
    except Exception as exc:  # noqa: BLE001
        # Includes "column not migrated yet" — see the fail-open note on the
        # pickup filter. Worst case the job is retried on the next schedule,
        # which is the pre-0018 behavior, not a new failure.
        logger.warning("could not record backoff on job=%s: %s", job_id, exc)


def _now() -> str:
    return _utc_now_iso()


def _touch_started(job_id: str) -> None:
    db.update("ingest_jobs", {"id": f"eq.{job_id}"},
              {"status": "in_progress", "started_at": _now(), "updated_at": _now()})


def _checkpoint(job_id, *, frontier, folders_expanded, items_stored, pdfs_fetched, status,
                seen=None) -> None:
    values = {
        "frontier": frontier,
        "folders_expanded": folders_expanded,
        "items_stored": items_stored,
        "pdfs_fetched": pdfs_fetched,
        "status": status,
        "updated_at": _now(),
    }
    # FIX A: the persisted expanded-container set. Written on every checkpoint
    # alongside the frontier so the two can never disagree about what has been
    # walked. Omitted (not sent as null) when the caller has nothing to say, so
    # a checkpoint from an older code path cannot blank it.
    if seen is not None:
        values["seen"] = sorted(seen)
    if status == "complete":
        values["finished_at"] = _now()
    db.update("ingest_jobs", {"id": f"eq.{job_id}"}, values)


def _mark_failed(job_id: str, error: str) -> None:
    db.update("ingest_jobs", {"id": f"eq.{job_id}"},
              {"status": "failed", "last_error": error[:2000],
               "updated_at": _now(), "finished_at": _now()})
