"""AI skill proposal with institution-wide dedup and a human-in-the-loop gate.

The problem this solves: MMCM has run a fully-digital Blackboard since 2018,
hundreds of courses, many shared or reused across departments (an engineering
course and an AEC course both covering Boolean logic, etc.). Hand-mapping a
skill graph per course via a CEA spreadsheet does not scale to that catalog.

The approach:
  1. Propose  - one reasoning-model call per course reads the course's
     ingested content (module/lesson/assessment text) and proposes a small
     set of canonical, *assessable* skills, each with a Bloom level and a
     blueprint weight. Guardrails live in the prompt: observable/assessable
     wording, no vague "understand X" skills, deduped within the proposal.
  2. Dedup across the institution - before writing any proposed skill, embed
     it and search every ALREADY-APPROVED skill in the institution (any
     course) via match_skills. Three outcomes by similarity:
       - >= AUTO_MATCH: treat as the same skill. Reuse the approved skill's
         name/bloom/weight, mark this course's row 'approved' immediately,
         and point canonical_skill_id at the origin. No human needed - it was
         already vetted once.
       - >= REVIEW_HINT (but < AUTO_MATCH): create as 'proposed' with the
         near-match noted, so the reviewer sees "possible duplicate of X".
       - < REVIEW_HINT: create as 'proposed', genuinely novel.
  3. Human-in-the-loop - anything 'proposed' waits for a human to approve or
     reject (via the review endpoints / a future admin screen / Supabase
     directly for the demo). Only 'approved' skills ever feed the twin,
     heatmap, or diagnostic.

The leverage: the first course through the pipeline needs real review; by the
Nth shared course, most proposals auto-match already-approved skills, so the
review burden shrinks as the catalog fills in.
"""
from __future__ import annotations

import json

from app.ai import bedrock, router as model_router
from app.db import supabase as db

# Similarity thresholds (cosine, 0..1). Tuned conservatively: better to send a
# borderline skill to a human than to silently collapse two distinct skills.
AUTO_MATCH = 0.92    # same skill; reuse the approved one, no review needed
REVIEW_HINT = 0.82   # likely duplicate; create as proposed, flag the match

# Guardrails for the proposal call. Kept here (not just in the prompt) so the
# intent is reviewable in code.
_SYSTEM = (
    "You extract a small set of CANONICAL, ASSESSABLE skills from course "
    "content for a mastery-tracking system. Rules:\n"
    "- Each skill must be observable and assessable: something a student "
    "demonstrably DOES. Prefer 'Construct a truth table' over 'Understand "
    "logic'. Never output vague skills like 'Understand embedded systems'.\n"
    "- Start each skill with a cognitive verb matching its Bloom level.\n"
    "- Deduplicate within your own output: if two activities exercise the "
    "same underlying skill, emit ONE skill, not two.\n"
    "- Prefer FEWER, higher-quality skills. A typical module yields 3-6.\n"
    "- bloom_level is the cognitive demand of the SKILL, one of: remember, "
    "understand, apply, analyze, evaluate, create.\n"
    "- weight is relative assessment importance, 0.5 (minor) to 2.0 (central "
    "to the course), default 1.0.\n"
    "Return ONLY JSON: {\"skills\": [{\"name\": ..., \"bloom_level\": ..., "
    "\"weight\": ...}, ...]}. No prose, no markdown fences."
)

_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


def _parse_proposals(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for s in data.get("skills", []):
        name = (s.get("name") or "").strip()
        bloom = s.get("bloom_level")
        if not name or bloom not in _BLOOM:
            continue  # drop malformed proposals rather than trust them
        try:
            weight = float(s.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        weight = max(0.5, min(2.0, weight))
        out.append({"name": name, "bloom_level": bloom, "weight": weight})
    return out


def propose_skills_from_text(*, course_content: str) -> list[dict]:
    """One reasoning-model call. Returns validated, in-proposal-deduped skill
    dicts (name, bloom_level, weight). Pure: no DB writes, easy to test."""
    raw = model_router.answer(
        system=_SYSTEM,
        user_text=json.dumps({"course_content": course_content})[:24000],
        escalate=True,  # skill design is worth the reasoning-tier model
    )
    return _parse_proposals(raw)


def _find_approved_match(*, institution_id: str, name: str) -> dict | None:
    """Nearest already-approved skill in the institution, or None."""
    emb = bedrock.embed(name, input_type="search_document")
    matches = db.rpc("match_skills", {
        "p_institution_id": institution_id,
        "p_query": emb,
        "p_match_count": 1,
    }) or []
    return matches[0] if matches else None


def seed_course_skills(
    *, institution_id: str, course_id: str, course_content: str,
    module_ref: str | None = None,
) -> dict:
    """Propose skills for a course and reconcile each against the institution's
    approved catalog. Idempotent-ish: skips proposing if the course already has
    any skills (approved or proposed), so a re-launch doesn't duplicate work.

    Returns counts for logging: proposed, auto_approved (matched), flagged.
    Best-effort by contract: the caller (launch handler) must treat a raised
    exception as non-fatal, this must never block a launch.
    """
    existing = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "select": "id", "limit": "1",
    })
    if existing:
        return {"skipped": True, "reason": "course already has skills"}

    proposals = propose_skills_from_text(course_content=course_content)
    proposed = auto_approved = flagged = 0

    for p in proposals:
        match = _find_approved_match(institution_id=institution_id, name=p["name"])
        sim = float(match["similarity"]) if match else 0.0
        emb = bedrock.embed(p["name"], input_type="search_document")

        if match and sim >= AUTO_MATCH:
            # Same skill, already vetted elsewhere. Reuse it verbatim and go
            # straight to approved, pointing at the canonical origin.
            db.insert("skills", [{
                "institution_id": institution_id, "course_id": course_id,
                "name": match["name"], "bloom_level": match["bloom_level"],
                "blueprint_weight": match["blueprint_weight"],
                "status": "approved",
                "canonical_skill_id": match["id"],
                "embedding": emb,
                "proposed_source": module_ref,
            }])
            auto_approved += 1
        else:
            # Novel, or only a possible duplicate: stage for human review.
            note = None
            if match and sim >= REVIEW_HINT:
                note = f"possible duplicate of '{match['name']}' (sim {sim:.2f})"
                flagged += 1
            db.insert("skills", [{
                "institution_id": institution_id, "course_id": course_id,
                "name": p["name"], "bloom_level": p["bloom_level"],
                "blueprint_weight": p["weight"],
                "status": "proposed",
                "embedding": emb,
                "proposed_source": note or module_ref,
            }])
            proposed += 1

    return {
        "skipped": False,
        "proposed": proposed,
        "auto_approved": auto_approved,
        "flagged_possible_duplicate": flagged,
    }
