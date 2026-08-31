"""Diagnostic endpoints. Full path: ingest, read course skills, generate
RAG-grounded questions, accept answers, grade server-side, write evidence
(service role), update the twin.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.ai import bedrock, router as model_router
from app.ai.chunking import chunk_text
from app.ai.concurrency import map_concurrent
from app.ai.deidentify import strip_pii
from app.ai.skill_proposer import seed_course_skills
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, get_lms_connector, require_role
from app.learn import items as item_gen
from app.lms.blackboard import BlackboardConnector
from app.lms.hierarchy import build_folder_paths, module_ref_for
from app.twin import summary as twin_summary
from app.twin import tracer

router = APIRouter(prefix="/courses", tags=["diagnostic"])


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
    # Folder/module scoping is resolved once, generically, over whatever tree
    # shape this institution's course actually has (see lms/hierarchy.py).
    # No assumption here about depth or naming, "Module N" vs a school that
    # organizes some other way both fall out of the same parent_id walk.
    folder_paths = build_folder_paths(content_items)
    skill_module_ref: dict[str, str] = {}  # first-tagged-item wins per skill
    stored = 0
    tagged = 0
    embedded = 0
    embed_failed = 0

    for item in content_items:
        body = item.get("body_or_description", "")
        if not body:
            continue
        item_folder_path = folder_paths.get(item.get("lms_content_id"), [])
        item_module_ref = module_ref_for(item_folder_path)
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
            row_id = rows[0]["id"]
            stored += 1

            tag = model_router.tag_content(text=clean_chunk, skills=skills)
            values = {}
            if tag["skill_id"]:
                values["skill_id"] = tag["skill_id"]
                tagged += 1
                # Best-effort skill -> module inference: the first content
                # item tagged to a skill decides that skill's module_ref.
                # A manual override (e.g. from the CEA spreadsheet) always
                # wins over this and is never touched here (only fills gaps).
                if item_module_ref and tag["skill_id"] not in skill_module_ref:
                    skill_module_ref[tag["skill_id"]] = item_module_ref
            if values:
                db.update("content_items", {"id": f"eq.{row_id}"}, values)

            # Best-effort: an embedding provider outage or a single flaky
            # chunk must not fail the whole ingest run (found necessary
            # live: a broken free embedding endpoint was previously enough
            # to 502 the entire request after the very first chunk). The
            # content row and its skill tag are already stored either way;
            # a chunk with no embedding just won't surface in RAG retrieval
            # (match_content_items filters on embedding is not null), which
            # degrades gracefully rather than failing outright.
            try:
                embedding = bedrock.embed(clean_chunk)
                if len(embedding) != 1024:
                    raise ValueError(f"embedding dimension was {len(embedding)}, expected 1024")
            except Exception as exc:
                print(f"embedding failed for a chunk of {item.get('lms_content_id')}: {exc}")
                embed_failed += 1
                continue
            db.update("content_items", {"id": f"eq.{row_id}"}, {"embedding": embedding})
            embedded += 1

    for skill_id, module_ref in skill_module_ref.items():
        # Only fill skills that don't already have a module_ref (a prior
        # manual override, or a prior ingest run, is never overwritten).
        db.update(
            "skills",
            {"id": f"eq.{skill_id}", "module_ref": "is.null"},
            {"module_ref": module_ref},
        )

    return {"stored": stored, "tagged": tagged, "embedded": embedded, "embedFailed": embed_failed}


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


@router.get("/{course_id}/diagnostic")
def get_diagnostic(
    course_id: str,
    module_ref: str | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    # module_ref lets a future UI scope the diagnostic to one module (e.g.
    # "just Module 2") once skills.module_ref is populated by ingest.
    # Omitted, this is unchanged: the whole course's skills, as before.
    skill_filters = {
        "course_id": f"eq.{course_id}", "institution_id": f"eq.{user.institution_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level", "limit": "10",
    }
    if module_ref is not None:
        skill_filters["module_ref"] = f"eq.{module_ref}"
    skills = db.select("skills", skill_filters)
    if not skills:
        return {"courseId": course_id, "questions": []}

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
