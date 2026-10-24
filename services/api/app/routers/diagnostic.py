"""Diagnostic endpoints. Full path: ingest, read course skills, generate
RAG-grounded questions, accept answers, grade server-side, write evidence
(service role), update the twin.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app import tagging
from app.ai import bedrock, documents
from app.ai.chunking import chunk_text
from app.ai.deidentify import strip_pii
from app.bank.kick import kick_bank
from app.bank.serving import bank_enabled, pick_diagnostic_items, record_exposure
from app.db import storage
from app.db import supabase as db
from app.deps import (
    CurrentUser,
    get_current_user,
    get_lms_connector,
    require_role,
    require_valid_course_id,
)
from app.learn import items as item_gen
from app.lms.blackboard import BlackboardConnector
from app.routers.ingest_jobs import enqueue_ingest, ingest_job_status
from app.routers.item_generation_jobs import enqueue_diagnostic
from app.twin import summary as twin_summary
from app.twin import tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["diagnostic"])

# A student with many unevidenced, actionable skills at once (e.g.
# first ever visit to a course with a large skill map) still only gets a
# short sitting. Count all actionable skills, then cap the available questions;
# unavailable skills never occupy sitting slots (DIAG-REQ-009–011).
MAX_DIAGNOSTIC_QUESTIONS = 10

# How long a single bounded phase may spend on network work before returning.
# The Lambda ceiling is 30s and API Gateway caps the request at 30s too, so a
# phase must finish well inside that and hand back whatever is left for the
# next call. Sized to leave room for the store phase and the response.
# How long the embed phase may spend before returning.
#
# Embedding is the only network phase left in these request handlers: tagging
# moved to the worker (see ingest_course's comment), because it is LLM-bound
# and cannot be made to fit a 30s request. The Lambda ceiling is 30s and API
# Gateway caps the request at 30s too, and this phase runs AFTER the LMS pull
# and the store step, so the budget is only part of the request.
#
# 12s, renamed from TAG_SLICE_SECONDS now that it no longer governs tagging.
# Embedding is one fast HTTP call per chunk with no reasoning, so it clears a
# course well inside this; the deadline is a backstop for a slow provider, not
# an expected limit.
EMBED_SLICE_SECONDS = 12.0


def _assert_teaches_course(*, user: CurrentUser, course_id: str) -> None:
    """The caller must be staff of THIS course, not merely staff somewhere.

    course_id comes from the path, so require_role alone is not enough — it
    only proves the caller holds a staff role in the institution. Mirrors the
    instructor dashboard's per-student check, at course scope. 404 rather than
    403 so an unauthorized staff member cannot distinguish a real course id
    from a fabricated one.
    """
    if user.app_role == "admin":
        return  # admins are institution-wide by definition
    rows = db.select("enrollments", {
        "institution_id": f"eq.{user.institution_id}",
        "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}",
        "role": "eq.instructor",
        "select": "course_id", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")


def _embed_pending(*, institution_id: str, course_id: str,
                   budget_seconds: float) -> tuple[int, int]:
    """Embed every chunk of this course that has no embedding yet.

    Embedding is one batched HTTP round trip per chunk (no LLM), so a whole
    course normally clears in one pass. Bounded anyway, because "normally" is
    not a guarantee and the failure mode we are fixing is exactly a phase that
    assumed it would finish.

    Returns (embedded, failed). A failure is counted, not raised: a chunk with
    no embedding simply will not surface in RAG retrieval, which is a graceful
    degradation (match_content_items filters on embedding is not null).
    """
    pending = db.select("content_items", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "embedding": "is.null", "select": "id,chunk_text",
    })
    embedded = failed = 0
    deadline = time.monotonic() + budget_seconds
    for row in pending:
        if time.monotonic() > deadline:
            break
        text = row.get("chunk_text") or ""
        if not text.strip():
            continue
        try:
            embedding = bedrock.embed(text)
            if len(embedding) != 1024:
                raise ValueError(f"embedding dimension was {len(embedding)}, expected 1024")
        except Exception as exc:  # noqa: BLE001 — degrade, do not fail the run
            logger.warning("embedding failed for content %s: %s", row["id"], exc)
            failed += 1
            continue
        db.update("content_items", {"id": f"eq.{row['id']}"}, {"embedding": embedding})
        embedded += 1
    return embedded, failed


def _course_ref(course_id: str, institution_id: str) -> str:
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{institution_id}",
        "select": "lms_course_id",
        "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    return courses[0]["lms_course_id"]


@router.get("/{course_id}/roster")
def get_roster(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    return connector.get_roster(_course_ref(course_id, user.institution_id))


@router.get("/{course_id}/content")
def get_content(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    # Cheap path on purpose: this is a debug/preview route for looking at the
    # content tree. It must NOT download and parse every PDF in the course.
    # include_attachments defaults False, so this stays a metadata walk.
    items, _stats = connector.get_content(_course_ref(course_id, user.institution_id))
    return items


@router.get("/{course_id}/assessments")
def get_assessments(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(require_role('instructor', 'admin')),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    try:
        _assert_teaches_course(user=user, course_id=course_id)
    except HTTPException as exc:
        # These gradebook routes expose course authorization denials as 403.
        # Keep the shared upload gate's 404 contract unchanged elsewhere.
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient course access") from exc
    return connector.get_assessments(_course_ref(course_id, user.institution_id))


@router.post("/{course_id}/skills/propose", status_code=status.HTTP_202_ACCEPTED)
def propose_course_skills(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(require_role('instructor', 'admin')),
):
    """Queue proposal work; the worker owns all model and content work."""
    now = datetime.now(UTC).isoformat()
    db.upsert("worker_state", [{"key": f"proposal:{course_id}", "value": {
        "status": "queued", "queued_at": now, "updated_at": now, "last_error": None,
    }}], on_conflict="key")
    kick_bank(course_id, "propose")
    return {"status": "queued"}


@router.post("/{course_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_course(
    course_id: str = Depends(require_valid_course_id),
    include_attachments: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    # INTEGRATION NOTE (this wiring was missing until now — see
    # docs/design/async-ingest.md): this route used to call
    # connector.get_content(...) synchronously right here, then store + embed
    # inline in this same request. That whole-tree walk measured 31.8s on a
    # real course (AWS101) — over the api Lambda's 30s wall before a single
    # PDF — so ingest silently timed out with no "Ingest pulled" log line
    # ever printed. That old body (dedupe query, per-item store loop,
    # _embed_pending call, pendingTagging count) is genuinely orphaned now
    # and should be removed in ITS OWN commit, separate from this one, per
    # the original patch note — `_embed_pending` itself stays, it is still
    # used by /content/upload below.
    #
    # No Blackboard call here any more. Enqueue and return immediately; the
    # worker's ingest_walk job (services/worker/app/jobs/ingest_walk.py)
    # drains the tree over its own schedule, checkpointing progress in
    # ingest_jobs so a killed run resumes.
    job = enqueue_ingest(
        institution_id=user.institution_id,
        course_id=course_id,
        include_attachments=include_attachments,
    )
    # 202 whether we created a job or found a live one; 200-with-existing
    # would be a lie (nothing new started) and an error would punish a
    # harmless retry or double-click.
    return {
        "status": "queued" if job["created"] else "already_in_progress",
        "job": job,
        "message": "Ingest runs in the background; poll GET /{course_id}/ingest/status.",
    }


@router.get("/{course_id}/ingest/status")
def ingest_status(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    job = ingest_job_status(course_id=course_id)
    if job is None:
        return {"status": "never_ingested", "job": None}
    return {"status": job["status"], "job": job}


@router.post("/{course_id}/content/upload")
def upload_course_content(
    course_id: str = Depends(require_valid_course_id),
    file: UploadFile = File(...),
    module_ref: str | None = Form(None),
    user: CurrentUser = Depends(require_role('instructor', 'admin')),
):
    """Staff upload of course material the LMS connector cannot reach.

    WHY THIS EXISTS. Blackboard's Learn REST API exposes `resource/x-bb-file`
    items as METADATA ONLY — fileName and mimeType, no download reference
    (verified live: /download and /file 404, the sole link is a browser-session
    Ultra redirect). So for a course whose real material is a shelf of PDFs
    (the AWS Academy module decks, the syllabus, the review sheets), ingest has
    nothing to read and the generator ends up writing questions from the skill
    name alone. This is the escape hatch: a human with the files uploads them
    directly, they land in content_items, and they go through the SAME tagging
    and embedding path ingest uses — so they behave exactly like scraped
    content downstream, including feeding RAG retrieval and generation.

    Deliberately NOT the tutor_attachments path. That table is a student's own
    private material for one conversation: not shared, not skill-tagged, not
    part of the course corpus. Reusing it would have looked like a shortcut and
    produced a file that no generation surface could ever see.

    Gate: two layers, because course_id is caller-supplied. require_role proves
    the caller is staff somewhere; _assert_teaches_course proves it is THIS
    course. Same shape as the instructor dashboard's checks.
    """
    _assert_teaches_course(user=user, course_id=course_id)

    filename = documents.safe_filename(file.filename)
    try:
        mime_type = documents.resolve_mime_type(filename, file.content_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    content = file.file.read()
    if len(content) > documents.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"file exceeds {documents.MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
        )

    try:
        text = documents.extract_text(content, mime_type)
    except Exception as exc:
        # A PDF that will not parse is the caller's problem to fix (wrong file,
        # corrupt export), and they are staff who can act on it — so say so
        # rather than silently storing a file that contributes nothing.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"could not read text from {filename}: {exc}",
        ) from exc
    if not text.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{filename} contained no extractable text (a scanned/image PDF needs OCR first)",
        )

    # Provenance: keep the original bytes so the corpus can be audited and a
    # re-parse (better OCR, a different extractor) is possible without asking
    # staff for the file again. Failure to store is not fatal to the ingest —
    # the extracted text is what actually feeds generation.
    upload_ref = f"course-content/{course_id}/{filename}"
    stored_original = True
    try:
        storage.upload(upload_ref, content, mime_type)
    except Exception as exc:  # noqa: BLE001 — provenance is nice-to-have
        logger.warning("could not archive %s for course %s: %s", filename, course_id, exc)
        stored_original = False

    # Store chunks here, then reuse ingest's _embed_pending. Its 12s phase
    # budget is checked between chunks; it does not cancel an in-flight
    # embedding or DB call. Extraction, original storage, chunk inserts, and
    # the pending query are outside that budget. There is no whole-request
    # deadline, so a large PDF or slow dependency can exceed the 30s Lambda
    # ceiling. Tagging is queued for the worker's tag_recompute job.
    clean = strip_pii(text)
    rows = []
    for chunk in chunk_text(clean):
        inserted = db.insert("content_items", [{
            "institution_id": user.institution_id,
            "course_id": course_id,
            # lms_ref is null: this content has no LMS counterpart, which is
            # the whole reason it was uploaded. Kept distinct from scraped
            # rows so a future re-ingest does not treat it as one.
            "lms_ref": None,
            "parent_lms_ref": None,
            "folder_path": [],
            "module_ref": module_ref,
            "chunk_text": chunk,
        }])
        if inserted:
            rows.append(inserted[0]["id"])

    embedded, embed_failed = _embed_pending(
        institution_id=user.institution_id, course_id=course_id,
        budget_seconds=EMBED_SLICE_SECONDS,
    )

    pending_tag_count = len(db.select("content_items", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "tag_attempted_at": "is.null", "select": "id",
    }))

    return {
        "filename": filename,
        "mimeType": mime_type,
        "stored": len(rows),
        "embedded": embedded,
        "embedFailed": embed_failed,
        "originalArchived": stored_original,
        # Chunks the worker will tag on its next scheduled run. Reported for
        # observability, not as something to poll on.
        "pendingTagging": pending_tag_count,
        "tagging": "queued for the worker's tag_recompute job",
    }


@router.post("/{course_id}/content/retag")
def reset_tagging(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(require_role('instructor', 'admin')),
):
    """Recompute every embedded course chunk against approved skill vectors.

    The operation is a single database RPC, performs no model calls, and is
    intentionally a full recompute so rejected or newly approved skills are
    reflected immediately.
    """
    _assert_teaches_course(user=user, course_id=course_id)

    result = tagging.tag_recompute(course_id=course_id, institution_id=user.institution_id)
    return {
        "courseId": course_id,
        "tagged": int(result.get("tagged") or 0),
        "belowThreshold": int(result.get("below_threshold") or 0),
        "ambiguous": int(result.get("ambiguous") or 0),
    }


@router.get("/{course_id}/modules")
def list_modules(
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    """Distinct modules detected for this course from the last ingest run,
    with content and skill counts. Generic over however this institution's
    Blackboard course is actually organized, no naming assumed. Useful for
    an admin screen to sanity-check ingest, and as the source of options for
    any future module-scoped filtering in the UI."""
    content_rows = db.select("content_items", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "select": "module_ref",
    })
    skill_rows = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "select": "module_ref",
    })
    content_counts: dict[str | None, int] = {}
    for r in content_rows:
        content_counts[r["module_ref"]] = content_counts.get(r["module_ref"], 0) + 1
    skill_counts: dict[str | None, int] = {}
    for r in skill_rows:
        skill_counts[r["module_ref"]] = skill_counts.get(r["module_ref"], 0) + 1

    modules = sorted(
        {ref for ref in content_counts if ref} | {ref for ref in skill_counts if ref}
    )
    return {
        "courseId": course_id,
        "modules": [{
            "moduleRef": m,
            "contentItemCount": content_counts.get(m, 0),
            "skillCount": skill_counts.get(m, 0),
        } for m in modules],
        "unscopedContentItemCount": content_counts.get(None, 0),
        "unscopedSkillCount": skill_counts.get(None, 0),
    }


class SubmitAnswer(BaseModel):
    item_id: str
    choice_id: str
    latency_ms: int = 0


class SubmitBody(BaseModel):
    answers: list[SubmitAnswer]


class GradeBody(BaseModel):
    user_id: str
    score: float


@router.patch("/{course_id}/assessments/{column_id}/grade")
def post_grade(
    body: GradeBody,
    column_id: str,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(require_role('instructor', 'admin')),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    try:
        _assert_teaches_course(user=user, course_id=course_id)
    except HTTPException as exc:
        # Match assessment reads without changing the shared upload gate.
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient course access") from exc
    connector.post_grade(
        _course_ref(course_id, user.institution_id),
        column_id,
        body.user_id,
        body.score,
    )
    return {"courseId": course_id, "columnId": column_id, "userId": body.user_id, "score": body.score}


def _diagnostic_rows(table: str, params: dict[str, str]) -> list[dict]:
    """Ordered paging avoids treating a truncated history as no evidence."""
    rows: list[dict] = []
    while True:
        page = db.select(table, {**params, "limit": "500", "offset": str(len(rows))})
        rows.extend(page)
        if len(page) < 500:
            return rows


def _skills_needing_diagnostic(
    *, institution_id: str, course_id: str, user_id: str, module_ref: str | None = None,
) -> list[dict]:
    """Approved skills without ANY learner evidence or recorded item review.

    This is eligibility only. Both endpoints then use the same availability
    calculation before counting or applying the sitting limit (DIAG-REQ-009).
    A claimed/served item alone is not evidence of studying or answering.
    """
    skill_filters = {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "status": "eq.approved", "select": "id,name,bloom_level",
        "order": "created_at.asc,id.asc",
    }
    if module_ref is not None:
        skill_filters["module_ref"] = f"eq.{module_ref}"
    skills = _diagnostic_rows("skills", skill_filters)
    evidenced: set[str] = set()
    for start in range(0, len(skills), 100):
        ids = ','.join(skill["id"] for skill in skills[start:start + 100])
        filters = {
            "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
            "user_id": f"eq.{user_id}", "skill_id": f"in.({ids})",
            "select": "skill_id", "order": "id.asc",
        }
        # Reviews are actual Study/Practice activity even when they do not
        # produce mastery evidence. Reading them does not change that policy.
        for table in ("evidence_events", "item_reviews"):
            evidenced.update(row["skill_id"] for row in _diagnostic_rows(table, filters))
    return [skill for skill in skills if skill["id"] not in evidenced]


def _diagnostic_availability(
    *, institution_id: str, course_id: str, user_id: str,
    module_ref: str | None, prepare_missing: bool = False,
) -> dict:
    """Shared availability snapshot; status uses SELECTs only (DIAG-REQ-010/011)."""
    skills = _skills_needing_diagnostic(
        institution_id=institution_id, course_id=course_id, user_id=user_id,
        module_ref=module_ref,
    )
    empty = {"items": [], "pendingSkillIds": [], "failedSkillIds": [],
             "waitingForMaterialCount": 0}
    if not skills:
        return empty
    scope = {"institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}"}
    courses = db.select("courses", {
        "institution_id": f"eq.{institution_id}", "id": f"eq.{course_id}",
        "select": "id,bank_serving", "limit": "1",
    })
    use_bank = bool(courses and bank_enabled(courses[0], "diagnostic"))
    states: dict[str, dict] = {}
    jobs: dict[str, dict] = {}
    items: dict[str, dict] = {}
    for start in range(0, len(skills), 100):
        skill_filter = f"in.({','.join(s['id'] for s in skills[start:start + 100])})"
        for row in _diagnostic_rows("skill_bank_state", {
            **scope, "skill_id": skill_filter,
            "select": "skill_id,status", "order": "skill_id.asc",
        }):
            states[row["skill_id"]] = row
        if not use_bank:
            for row in _diagnostic_rows("generated_items", {
                **scope, "skill_id": skill_filter, "kind": "eq.diagnostic",
                "retired_at": "is.null",
                "select": "id,skill_id,bloom_level,prompt,choices",
                "order": "created_at.asc,id.asc",
            }):
                items.setdefault(row["skill_id"], row)
            for row in _diagnostic_rows("item_generation_jobs", {
                **scope, "skill_id": skill_filter, "kind": "eq.diagnostic",
                "select": "skill_id,status,last_error", "order": "created_at.desc,id.desc",
            }):
                jobs.setdefault(row["skill_id"], row)
    if use_bank:
        items = pick_diagnostic_items(
            user_id, course_id, [s["id"] for s in skills], institution_id=institution_id,
        )
    elif prepare_missing:
        # Retain the existing worker enqueue path and its ten-skill request
        # bound. Later skills remain pending without claiming a worker is live.
        missing = [s for s in skills if s["id"] not in items
                   and states.get(s["id"], {}).get("status") != "no_material"]
        # Existing terminal jobs must not consume the enqueue allowance and
        # indefinitely block later skills that have never requested a question.
        unqueued = [skill for skill in missing if skill["id"] not in jobs]
        for skill in unqueued[:MAX_DIAGNOSTIC_QUESTIONS]:
            jobs[skill["id"]], _created = enqueue_diagnostic(
                institution_id=institution_id, course_id=course_id, skill_id=skill["id"],
            )
        # Preserve the worker-completion race re-read, across all candidates.
        if missing:
            for start in range(0, len(skills), 100):
                ids = ','.join(s["id"] for s in skills[start:start + 100])
                for row in _diagnostic_rows("generated_items", {
                    **scope, "skill_id": f"in.({ids})", "kind": "eq.diagnostic",
                    "retired_at": "is.null",
                    "select": "id,skill_id,bloom_level,prompt,choices",
                    "order": "created_at.asc,id.asc",
                }):
                    items.setdefault(row["skill_id"], row)

    ready, pending, failed = [], [], []
    waiting_for_material = 0
    for skill in skills:
        sid = skill["id"]
        state = states.get(sid, {})
        job = jobs.get(sid, {})
        if state.get("status") == "no_material":
            waiting_for_material += 1
        elif sid in items:
            ready.append(items[sid])
        elif not use_bank and job.get("last_error") == "NoCourseContentError":
            waiting_for_material += 1
        elif ((use_bank and state.get("status") == "error")
              or (not use_bank and job.get("status") == "failed")):
            failed.append(sid)
        else:
            pending.append(sid)
    if use_bank and prepare_missing and pending:
        kick_bank(course_id, "diagnostic")
    return {"items": ready, "pendingSkillIds": pending, "failedSkillIds": failed,
            "waitingForMaterialCount": waiting_for_material}


@router.get("/{course_id}/diagnostic/status")
def get_diagnostic_status(
    course_id: str = Depends(require_valid_course_id),
    module_ref: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Read actionable availability without generation, kicks or evidence writes."""
    availability = _diagnostic_availability(
        institution_id=user.institution_id, course_id=course_id,
        user_id=user.user_id, module_ref=module_ref,
    )
    due = len(availability["items"])
    return {"courseId": course_id, "due": due > 0, "dueSkillCount": due,
            "waitingForMaterialCount": availability["waitingForMaterialCount"]}


@router.get("/{course_id}/diagnostic")
def get_diagnostic(
    course_id: str = Depends(require_valid_course_id),
    module_ref: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    availability = _diagnostic_availability(
        institution_id=user.institution_id, course_id=course_id,
        user_id=user.user_id, module_ref=module_ref, prepare_missing=True,
    )
    questions = [{
        "id": item["id"], "skillId": item["skill_id"],
        "bloomLevel": item.get("bloom_level"), "prompt": item["prompt"],
        "choices": item.get("choices") or [],
    } for item in availability["items"][:MAX_DIAGNOSTIC_QUESTIONS]]
    pending, failed = availability["pendingSkillIds"], availability["failedSkillIds"]
    status_value = ("ready" if questions else "generating" if pending
                    else "failed" if failed else "ready")
    return {
        "courseId": course_id, "status": status_value, "questions": questions,
        "readyCount": len(questions), "pendingSkillIds": pending,
        "failedSkillIds": failed, "skippedSkillCount": len(failed),
        "waitingForMaterialCount": availability["waitingForMaterialCount"],
    }


@router.post("/{course_id}/diagnostic/submit")
def submit_diagnostic(
    body: SubmitBody,
    course_id: str = Depends(require_valid_course_id),
    user: CurrentUser = Depends(get_current_user),
):
    results = []
    rows = []
    for a in body.answers:
        try:
            graded = item_gen.grade(
                institution_id=user.institution_id, item_id=a.item_id, choice_id=a.choice_id,
            )
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"item {a.item_id} not found")
        results.append({**graded, "itemId": a.item_id})
        rows.append({
            "institution_id": user.institution_id, "user_id": user.user_id,
            "course_id": course_id, "skill_id": graded["skillId"], "type": "diagnostic",
            "correct": graded["correct"], "latency_ms": a.latency_ms,
        })
        record_exposure(
            institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
            skill_id=graded["skillId"], item_id=a.item_id,
            tested=True, answered=True, correct=graded["correct"],
        )
    if rows:
        db.insert_evidence(rows)

    # Mastery delta: the diagnostic is the one moment every mapped skill in
    # the course moves at once, from no-evidence to a real baseline. Capture
    # the "before" state up front (a fresh skill has no mastery_state row at
    # all, which is the no-evidence case, distinct from a 0.0 estimate) so
    # the response can show the actual before/after for each skill touched,
    # not just a correct-count. The client never computes bands itself; this
    # mirrors how app/twin/summary.py already does the estimate-to-band
    # mapping for every other surface.
    touched_skill_ids = sorted({r["skillId"] for r in results})
    prior_rows = db.select("mastery_state", {
        "user_id": f"eq.{user.user_id}",
        "skill_id": f"in.({','.join(touched_skill_ids)})",
        "select": "skill_id,estimate",
    }) if touched_skill_ids else []
    prior_estimate = {r["skill_id"]: float(r["estimate"]) for r in prior_rows}

    posterior_estimate: dict[str, float] = {}
    for r in results:
        state = tracer.apply_evidence(
            institution_id=user.institution_id, user_id=user.user_id,
            course_id=course_id, skill_id=r["skillId"], correct=r["correct"],
        )
        posterior_estimate[r["skillId"]] = float(state["estimate"])

    skill_names = {}
    if touched_skill_ids:
        skill_rows = db.select("skills", {
            "id": f"in.({','.join(touched_skill_ids)})", "select": "id,name",
        })
        skill_names = {s["id"]: s["name"] for s in skill_rows}

    mastery_delta = [{
        "skillId": skill_id,
        "skillName": skill_names.get(skill_id, "Unknown skill"),
        "priorEstimate": prior_estimate.get(skill_id),
        "priorBand": twin_summary.band_for(prior_estimate.get(skill_id)),
        "posteriorEstimate": posterior_estimate[skill_id],
        "posteriorBand": twin_summary.band_for(posterior_estimate[skill_id]),
    } for skill_id in touched_skill_ids]

    correct = sum(1 for r in results if r["correct"])
    return {
        "correctCount": correct,
        "total": len(results),
        "results": [{"itemId": r["itemId"], "correct": r["correct"], "explanation": r["explanation"]} for r in results],
        "masteryDelta": mastery_delta,
    }
