"""Diagnostic endpoints. Full path: ingest, read course skills, generate
RAG-grounded questions, accept answers, grade server-side, write evidence
(service role), update the twin.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.ai import bedrock, documents, router as model_router
from app.ai.chunking import chunk_text
from app.ai.concurrency import map_concurrent
from app.ai.deidentify import strip_pii
from app.ai.skill_proposer import seed_course_skills
from app.db import storage, supabase as db
from app.deps import CurrentUser, get_current_user, get_lms_connector, require_role
from app.learn import items as item_gen
from app.lms.blackboard import BlackboardConnector
from app.lms.hierarchy import build_folder_paths, module_ref_for
from app.twin import summary as twin_summary
from app.twin import tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["diagnostic"])

# A student who is far behind (many skills never diagnosed at once, e.g.
# first ever visit to a course with a large skill map) still only gets a
# short sitting, not everything at once. The rest stays due and simply
# resurfaces next time — status reports the TRUE due count, uncapped, so
# the notification is honest about total volume even though one sitting
# only serves this many.
MAX_DIAGNOSTIC_QUESTIONS = 10

# How long a single bounded phase may spend on network work before returning.
# The Lambda ceiling is 30s and API Gateway caps the request at 30s too, so a
# phase must finish well inside that and hand back whatever is left for the
# next call. Sized to leave room for the store phase and the response.
TAG_SLICE_SECONDS = 12.0


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


def _tag_pending(*, institution_id: str, course_id: str, skills: list[dict],
                 budget_seconds: float) -> tuple[int, int]:
    """Tag chunks that have no skill yet, for as long as the budget allows.

    This is the expensive phase — one LLM call per chunk — and the one that
    used to blow the Lambda's ceiling. It selects chunks still missing a
    skill_id, works through them until the deadline, and returns how many are
    left. Calling ingest again resumes exactly here, because the ROWS are the
    progress record: a chunk with a skill_id is done, one without is not.

    Returns (tagged, remaining).
    """
    if not skills:
        # Nothing to tag against. Reported as 0 remaining rather than looping
        # forever on chunks that can never be tagged (the course simply has no
        # approved skills yet — see the skills/propose endpoint).
        return 0, 0

    pending = db.select("content_items", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        # tag_attempted_at, NOT skill_id: a chunk the model legitimately cannot
        # match to any skill must stop being "pending" or `remaining` never
        # reaches zero and a caller loops forever on untaggable content.
        "tag_attempted_at": "is.null", "select": "id,chunk_text,module_ref",
    })
    tagged = 0
    skill_module_ref: dict[str, str] = {}
    deadline = time.monotonic() + budget_seconds

    for row in pending:
        if time.monotonic() > deadline:
            break
        text = row.get("chunk_text") or ""
        if not text.strip():
            # Nothing to tag, and nothing will change on a retry. Mark it
            # attempted so it does not sit in the pending set forever.
            db.update("content_items", {"id": f"eq.{row['id']}"},
                      {"tag_attempted_at": datetime.now(timezone.utc).isoformat()})
            continue
        try:
            tag = model_router.tag_content(text=text, skills=skills)
        except Exception as exc:  # noqa: BLE001 — a flaky tag must not kill the run
            # Deliberately do NOT mark this attempted: a provider failure is
            # transient, and leaving it pending is what makes a later run
            # retry it once the tagger is healthy again.
            logger.warning("tagging failed for content %s: %s", row["id"], exc)
            continue
        skill_id = tag.get("skill_id")
        update = {"tag_attempted_at": datetime.now(timezone.utc).isoformat()}
        if skill_id:
            update["skill_id"] = skill_id
        db.update("content_items", {"id": f"eq.{row['id']}"}, update)
        if skill_id:
            tagged += 1
            module_ref = row.get("module_ref")
            if module_ref and skill_id not in skill_module_ref:
                skill_module_ref[skill_id] = module_ref

    # Best-effort skill -> module inference: the first tagged chunk for a skill
    # decides that skill's module_ref, and a manual override is never touched
    # (only fills gaps). Same behaviour as before, just applied per slice.
    for skill_id, module_ref in skill_module_ref.items():
        db.update("skills",
                  {"id": f"eq.{skill_id}", "module_ref": "is.null"},
                  {"module_ref": module_ref})

    remaining = db.select("content_items", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "tag_attempted_at": "is.null", "select": "id",
    })
    return tagged, len(remaining)


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
def get_roster(course_id: str,
               user: CurrentUser = Depends(get_current_user),
               connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_roster(_course_ref(course_id, user.institution_id))


@router.get("/{course_id}/content")
def get_content(course_id: str,
                user: CurrentUser = Depends(get_current_user),
                connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_content(_course_ref(course_id, user.institution_id))


@router.get("/{course_id}/assessments")
def get_assessments(course_id: str,
                    user: CurrentUser = Depends(get_current_user),
                    connector: BlackboardConnector = Depends(get_lms_connector)):
    return connector.get_assessments(_course_ref(course_id, user.institution_id))


@router.post("/{course_id}/skills/propose")
def propose_course_skills(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """On-demand trigger for AI skill proposal, standalone, no relaunch
    needed. This was previously only ever fired as a side effect buried
    inside the LTI launch handler, meaning re-testing or re-running it
    required faking a fresh Blackboard launch each time. Same underlying
    pipeline (ai/skill_proposer.seed_course_skills), same idempotency
    behavior: if this course already has any skill rows, approved or
    proposed, this is a no-op, delete them first (in Supabase) if you
    genuinely want a from-scratch re-proposal, e.g. after fixing a bug in
    the proposal logic itself, or want to re-run against changed course
    content.
    """
    course_ref = _course_ref(course_id, user.institution_id)
    content_items = connector.get_content(course_ref)
    return seed_course_skills(
        institution_id=user.institution_id, course_id=course_id,
        content_items=content_items,
    )


@router.post("/{course_id}/ingest")
def ingest_course(course_id: str,
                  user: CurrentUser = Depends(get_current_user),
                  connector: BlackboardConnector = Depends(get_lms_connector)):
    course_ref = _course_ref(course_id, user.institution_id)
    skills = db.select("skills", {
        "course_id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "status": "eq.approved",  # tag content only against reviewed skills
        "select": "id,name",
    })
    content_items = connector.get_content(course_ref)

    # Diagnostic breadcrumb. The reason this exists: the course silently
    # ingested FIVE items, all from one folder branch, and nothing reported
    # that the AWS modules were never walked — it just looked like a small
    # course. Logging what the connector actually returned (how many items,
    # which handler types) makes a shallow traversal visible on the very first
    # run instead of being inferred from bad questions weeks later.
    handler_counts: dict[str, int] = {}
    for item in content_items:
        key = item.get("content_type") or "(none)"
        handler_counts[key] = handler_counts.get(key, 0) + 1
    with_body = sum(
        1 for item in content_items if (item.get("body_or_description") or "").strip()
    )
    logger.info(
        "Ingest pulled %d content items for course=%s (with text: %d, types: %s)",
        len(content_items), course_id, with_body, handler_counts,
    )

    # Folder/module scoping is resolved once, generically, over whatever tree
    # shape this institution's course actually has (see lms/hierarchy.py).
    # No assumption here about depth or naming, "Module N" vs a school that
    # organizes some other way both fall out of the same parent_id walk.
    folder_paths = build_folder_paths(content_items)

    # ---- Phase 1: store every chunk (cheap, pure DB) ----------------------
    #
    # WHY THIS IS SPLIT FROM TAGGING. This endpoint used to store, tag AND
    # embed each chunk in one serial loop. Tagging is one LLM call per chunk, so
    # a real course blew through the Lambda's 30s ceiling and was killed
    # mid-run — observed three times at exactly 30.000s, which is why the
    # course held 5 chunks while the connector returns 178 items. The run wrote
    # what it had reached and died, so the partial result looked like a small
    # course rather than a failed job.
    #
    # Storing is fast and idempotent-ish, so it all happens here in one call.
    # Tagging and embedding then work from the ROWS THAT EXIST, which makes the
    # rows themselves the progress record: no job table, no cursor to lose, and
    # a killed run is resumable by simply calling again.
    stored_rows: list[tuple[str, str]] = []  # (row_id, clean_chunk)
    for item in content_items:
        body = item.get("body_or_description", "")
        if not body:
            continue
        item_folder_path = folder_paths.get(item.get("lms_content_id"), [])
        item_module_ref = module_ref_for(item_folder_path)

        # Skip an item already ingested for this course: re-running ingest
        # after a timeout must not duplicate every chunk it already stored.
        existing = db.select("content_items", {
            "institution_id": f"eq.{user.institution_id}",
            "course_id": f"eq.{course_id}",
            "lms_ref": f"eq.{item.get('lms_content_id')}",
            "select": "id", "limit": "1",
        })
        if existing:
            continue

        for chunk in chunk_text(body):
            clean_chunk = strip_pii(chunk)
            rows = db.insert("content_items", [{
                "institution_id": user.institution_id,
                "course_id": course_id,
                "lms_ref": item.get("lms_content_id"),
                "parent_lms_ref": item.get("parent_id"),
                "folder_path": item_folder_path,
                "module_ref": item_module_ref,
                "chunk_text": clean_chunk,
            }])
            if not rows:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "content row was not stored")
            stored_rows.append((rows[0]["id"], clean_chunk))

    # ---- Phase 2: embed what has no embedding yet (network, bounded) ------
    # Embeddings are the cheap network call (one batched HTTP round trip each,
    # no LLM), so this clears a whole course in one pass. Still bounded by a
    # deadline so a very large course cannot reintroduce the timeout.
    embedded, embed_failed = _embed_pending(
        institution_id=user.institution_id, course_id=course_id,
        budget_seconds=TAG_SLICE_SECONDS,
    )

    # ---- Phase 3: tag a bounded slice (LLM, slow, RESUMABLE) --------------
    # One LLM call per chunk is the expensive part, so this does as many as fit
    # in the time budget and stops cleanly. Whatever is left is picked up by the
    # next call — see _tag_pending, which selects chunks still missing a tag.
    tagged, remaining = _tag_pending(
        institution_id=user.institution_id, course_id=course_id,
        skills=skills, budget_seconds=TAG_SLICE_SECONDS,
    )

    return {
        "stored": len(stored_rows),
        "tagged": tagged,
        "embedded": embedded,
        "embedFailed": embed_failed,
        # Non-zero means the course is NOT fully ingested yet: call again.
        # The client (or an operator) loops until this reads 0. A bare 200 on
        # this endpoint never meant "complete" — that is the lesson from the
        # 5-chunk course, so the response now says so explicitly.
        "remaining": remaining,
        "complete": remaining == 0,
    }


@router.post("/{course_id}/content/upload")
def upload_course_content(
    course_id: str,
    file: UploadFile = File(...),
    module_ref: str | None = Form(None),
    user: CurrentUser = Depends(require_role("instructor", "admin")),
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

    # Store the chunks, then run the SAME bounded phases ingest uses. Reusing
    # _embed_pending/_tag_pending (rather than tagging inline here) means an
    # upload is subject to exactly the same budget discipline — a large PDF
    # cannot time out the request, it just leaves work for the next call.
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

    skills = db.select("skills", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved", "select": "id,name",
    })
    embedded, embed_failed = _embed_pending(
        institution_id=user.institution_id, course_id=course_id,
        budget_seconds=TAG_SLICE_SECONDS,
    )
    tagged, remaining = _tag_pending(
        institution_id=user.institution_id, course_id=course_id,
        skills=skills, budget_seconds=TAG_SLICE_SECONDS,
    )

    return {
        "filename": filename,
        "mimeType": mime_type,
        "stored": len(rows),
        "tagged": tagged,
        "embedded": embedded,
        "embedFailed": embed_failed,
        "originalArchived": stored_original,
        "remaining": remaining,
        "complete": remaining == 0,
    }


@router.post("/{course_id}/content/retag")
def reset_tagging(
    course_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
):
    """Clear the "already attempted" mark on UNMATCHED content so it can be
    tagged again against a changed skill set.

    WHY THIS IS NEEDED AND WHY IT IS EXPLICIT. Ingest is resumable via
    `tag_attempted_at`: a chunk that has been through the tagger stops being
    pending, whether or not it matched a skill. That is what stops untaggable
    content looping forever — but it also means a plain re-run of /ingest
    retries NOTHING. Approving new skills and calling /ingest again would skip
    every chunk that previously found no match, which is precisely the content
    the new skills were approved to catch.

    So this is the deliberate second half of "approve skills, then retag":
    reset first, then ingest. Returns how many rows were reopened so the caller
    knows whether a re-tag is even worth running (0 means nothing to do).

    Only touches skill_id IS NULL rows. A chunk that already matched a skill
    keeps its tag and is not re-sent to the model — re-tagging matched content
    would be wasted calls and could reshuffle a correct match to a worse one.

    Staff-gated at both layers, like the upload endpoint: course_id is
    caller-supplied, so "staff somewhere" is not sufficient.
    """
    _assert_teaches_course(user=user, course_id=course_id)

    unmatched = db.select("content_items", {
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}",
        "skill_id": "is.null",
        "tag_attempted_at": "not.is.null",
        "select": "id",
    })
    reopened = 0
    for row in unmatched:
        db.update("content_items", {"id": f"eq.{row['id']}"}, {"tag_attempted_at": None})
        reopened += 1

    # Count what a following /ingest would actually pick up, so the caller is
    # not left guessing whether the two-step dance worked.
    total_unmatched = db.select("content_items", {
        "institution_id": f"eq.{user.institution_id}",
        "course_id": f"eq.{course_id}",
        "skill_id": "is.null", "select": "id",
    })
    return {
        "courseId": course_id,
        "reopened": reopened,
        "pendingAfterReset": len(total_unmatched),
        "next": (
            "POST /courses/{id}/ingest until complete=true" if total_unmatched
            else "nothing to retag"
        ),
    }


@router.get("/{course_id}/modules")
def list_modules(course_id: str, user: CurrentUser = Depends(get_current_user)):
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
def post_grade(course_id: str, column_id: str, body: GradeBody,
               user: CurrentUser = Depends(get_current_user),
               connector: BlackboardConnector = Depends(get_lms_connector)):
    connector.post_grade(
        _course_ref(course_id, user.institution_id),
        column_id,
        body.user_id,
        body.score,
    )
    return {"courseId": course_id, "columnId": column_id, "userId": body.user_id, "score": body.score}


def _skills_needing_diagnostic(
    *, institution_id: str, course_id: str, user_id: str, module_ref: str | None = None,
) -> list[dict]:
    """Approved skills this SPECIFIC student has never given diagnostic
    evidence for. This is the "is there something new to baseline" check,
    per student, not per course. A skill only drops off this list once this
    user has actually answered a diagnostic question for it, so a skill the
    instructor adds mid-term (or one this student simply hasn't reached
    yet) stays on it until they do. Deliberately distinct from
    generated_items existence, which only tracks whether a question has
    ever been WRITTEN for the skill course-wide (the shared item bank),
    not whether THIS student has taken it. Used both by GET /diagnostic
    (to decide what to include) and GET /diagnostic/status (to decide
    whether the diagnostic should even surface as available)."""
    skill_filters = {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{institution_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level",
        # Deterministic order so a student with more than
        # MAX_DIAGNOSTIC_QUESTIONS due gets the SAME slice on every
        # refetch, not an arbitrary 10 each time. created_at is stable and
        # already indexed via the primary key's default ordering behavior
        # elsewhere in this file (see cohort.py's own created_at ordering).
        "order": "created_at.asc",
    }
    if module_ref is not None:
        skill_filters["module_ref"] = f"eq.{module_ref}"
    skills = db.select("skills", skill_filters)
    if not skills:
        return []

    skill_ids = [s["id"] for s in skills]
    diagnosed_rows = db.select("evidence_events", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "user_id": f"eq.{user_id}", "type": "eq.diagnostic",
        "skill_id": f"in.({','.join(skill_ids)})",
        "select": "skill_id",
    })
    diagnosed_skill_ids = {r["skill_id"] for r in diagnosed_rows}
    return [s for s in skills if s["id"] not in diagnosed_skill_ids]


@router.get("/{course_id}/diagnostic/status")
def get_diagnostic_status(
    course_id: str,
    module_ref: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Lightweight due-check for a notification badge. No generation
    happens here, just skill + evidence reads, so this is safe to poll from
    the workspace home or the sidebar without generating anything. The
    diagnostic should not sit open as a permanent default tab; it should
    surface only when there is something new for THIS student to baseline."""
    due_skills = _skills_needing_diagnostic(
        institution_id=user.institution_id, course_id=course_id,
        user_id=user.user_id, module_ref=module_ref,
    )
    return {
        "courseId": course_id,
        "due": len(due_skills) > 0,
        "dueSkillCount": len(due_skills),
    }


@router.get("/{course_id}/diagnostic")
def get_diagnostic(
    course_id: str,
    module_ref: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    # module_ref lets a future UI scope the diagnostic to one module (e.g.
    # "just Module 2") once skills.module_ref is populated by ingest.
    # Omitted, this covers every skill still due for this student.
    skills = _skills_needing_diagnostic(
        institution_id=user.institution_id, course_id=course_id,
        user_id=user.user_id, module_ref=module_ref,
    )
    if not skills:
        return {"courseId": course_id, "questions": []}
    skills = skills[:MAX_DIAGNOSTIC_QUESTIONS]

    # The diagnostic is a fixed baseline instrument ("Build your baseline"),
    # not a randomized quiz — the page copy promises "one question per
    # skill," singular, so re-fetching must return the SAME set every time,
    # not a fresh batch. Before this fix, every GET called generate_question
    # unconditionally, which meant a refetch (window refocus, a remount,
    # React Query's own defaults) silently created new generated_items rows
    # and swapped the question set out from under the student mid-session —
    # this is what "questions keep changing" was.
    #
    # Fix: check for an existing diagnostic item per skill first (course-wide,
    # shared across students taking this course's diagnostic — items have no
    # user_id, matching how flashcards' MCQ items are already shared), and
    # only generate for skills that don't have one yet. Same check-first
    # pattern already used in flashcards.py's deck top-up.
    skill_ids = [s["id"] for s in skills]
    existing_rows = db.select("generated_items", {
        "institution_id": f"eq.{user.institution_id}", "course_id": f"eq.{course_id}",
        "kind": "eq.diagnostic",
        "skill_id": f"in.({','.join(skill_ids)})",
        "select": "id,skill_id,bloom_level,prompt,choices",
    })
    # First existing item per skill wins; if somehow more than one exists for
    # a skill (e.g. a pre-fix duplicate), don't add to the confusion by
    # rotating between them — pick deterministically and move on.
    existing_by_skill: dict[str, dict] = {}
    for row in existing_rows:
        existing_by_skill.setdefault(row["skill_id"], row)

    skills_needing_items = [s for s in skills if s["id"] not in existing_by_skill]

    # One Bedrock call per skill still missing an item (RAG retrieval +
    # generation), each fully independent — parallelized so generating for
    # several skills at once is one round trip's worth of wall-clock time,
    # not several serial ones. See ai/concurrency.py.
    newly_generated = map_concurrent(
        lambda s: item_gen.generate_question(
            institution_id=user.institution_id, course_id=course_id,
            skill=s, kind="diagnostic",
        ),
        skills_needing_items,
    )
    new_by_skill = dict(zip((s["id"] for s in skills_needing_items), newly_generated))

    # Reassemble in the original skills order, whichever source each came
    # from, so the response shape is identical to before this fix.
    questions = []
    for s in skills:
        if s["id"] in existing_by_skill:
            item = existing_by_skill[s["id"]]
            questions.append({
                "id": item["id"], "skillId": item["skill_id"],
                "bloomLevel": item.get("bloom_level"),
                "prompt": item["prompt"], "choices": item["choices"],
            })
        else:
            questions.append(new_by_skill[s["id"]])

    return {"courseId": course_id, "questions": questions}


@router.post("/{course_id}/diagnostic/submit")
def submit_diagnostic(course_id: str, body: SubmitBody,
                      user: CurrentUser = Depends(get_current_user)):
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
