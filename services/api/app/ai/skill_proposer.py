"""AI skill proposal with institution-wide dedup and a human-in-the-loop gate.

The problem this solves: MMCM has run a fully-digital Blackboard since 2018,
hundreds of courses, many shared or reused across departments (an engineering
course and an AEC course both covering Boolean logic, etc.). Hand-mapping a
skill graph per course via a CEA spreadsheet does not scale to that catalog.

The approach:
  0. Group by module - content items are grouped by module_ref (see
     lms/hierarchy.py), and proposal runs ONCE PER MODULE, not once for the
     whole course. This was a real bug in the first version: a single
     whole-course call, with an arbitrary text cutoff, meant only the first
     module's content reliably reached the model at all for a genuinely
     content-rich course, later modules were silently starved. Grouping by
     module also means each proposed skill's module_ref is known directly
     from which group produced it, no inference needed at ingest time.
  1. Propose  - one reasoning-model call per MODULE reads that module's
     content (lesson/assessment text) and proposes a small set of canonical,
     *assessable* skills, each with a Bloom level and a blueprint weight.
     Guardrails live in the prompt: observable/assessable wording, no vague
     "understand X" skills, deduped within the module's own proposal.
  2. Dedup across the institution - before writing any proposed skill, embed
     it and search every ALREADY-APPROVED skill in the institution (any
     course, any module) via match_skills. Three outcomes by similarity:
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
from app.lms.hierarchy import build_folder_paths, module_ref_for

# Similarity thresholds (cosine, 0..1). Tuned conservatively: better to send a
# borderline skill to a human than to silently collapse two distinct skills.
AUTO_MATCH = 0.92    # same skill; reuse the approved one, no review needed
REVIEW_HINT = 0.82   # likely duplicate; create as proposed, flag the match
# In-batch near-duplicate threshold. Two proposals FROM THE SAME RUN whose
# names are at least this similar are flagged as probable duplicates of each
# other. Same value as REVIEW_HINT on purpose: the bar for "worth a human's
# attention as a possible dup" is identical whether the other side is an
# already-approved skill or another fresh proposal. NEVER auto-collapsed --
# two proposals from one run are both unvetted, so picking a winner between
# them is a review decision, which belongs to the human, not the machine.
INBATCH_DUP = 0.82

# Per-module content size cap. This is generous, not a real prompt-length
# limit, current default model (minimax-m3:free) supports a 1M-token
# context; this exists only to guard against one pathologically large single
# module (a course with everything dumped in one folder), not to trim normal
# content. The original version of this file capped the WHOLE COURSE at
# 24,000 characters in one call, which silently starved every module after
# the first on any real, content-rich course. Per-module + generous is the
# actual fix, not just a bigger number on the same design.
MAX_CHARS_PER_MODULE = 120_000

# Guardrails for the proposal call. Kept here (not just in the prompt) so the
# intent is reviewable in code.
_SYSTEM = (
    "You extract a small set of CANONICAL, ASSESSABLE skills from ONE "
    "module's course content for a mastery-tracking system. Rules:\n"
    "- Each skill must be observable and assessable: something a student "
    "demonstrably DOES. Prefer 'Construct a truth table' over 'Understand "
    "logic'. Never output vague skills like 'Understand embedded systems'.\n"
    "- Start each skill with a cognitive verb matching its Bloom level.\n"
    "- Deduplicate within your own output: if two activities exercise the "
    "same underlying skill, emit ONE skill, not two.\n"
    "- Prefer FEWER, higher-quality skills for THIS module. 3-6 is typical "
    "for one module's worth of content, not for an entire course.\n"
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
    """One reasoning-model call, for ONE module's content (see module
    docstring for why this must be per-module, not per-course). Returns
    validated, in-proposal-deduped skill dicts. Pure: no DB writes, easy to
    test."""
    raw = model_router.answer(
        system=_SYSTEM,
        user_text=json.dumps({"module_content": course_content})[:MAX_CHARS_PER_MODULE],
        escalate=True,  # skill design is worth the reasoning-tier model
    )
    return _parse_proposals(raw)


def _group_content_by_module(content_items: list[dict]) -> dict[str | None, str]:
    """Group content items' text by resolved module_ref (see
    lms/hierarchy.py), joined into one string per module. None is a real key
    here, content that lives at the course root with no enclosing folder, it
    still gets proposed, just without a module_ref attached to the result."""
    folder_paths = build_folder_paths(content_items)
    groups: dict[str | None, list[str]] = {}
    for item in content_items:
        body = item.get("body_or_description", "")
        if not body:
            continue
        ref = module_ref_for(folder_paths.get(item.get("lms_content_id"), []))
        groups.setdefault(ref, []).append(body)
    return {ref: "\n\n".join(texts) for ref, texts in groups.items()}


def _find_approved_match(*, institution_id: str, name: str) -> dict | None:
    """Nearest already-approved skill in the institution, or None."""
    emb = bedrock.embed(name, input_type="search_document")
    matches = db.rpc("match_skills", {
        "p_institution_id": institution_id,
        "p_query": emb,
        "p_match_count": 1,
    }) or []
    return matches[0] if matches else None


def _already_proposed_modules(*, institution_id: str, course_id: str) -> set[str | None]:
    """Which module_refs already have at least one skill row for this course,
    i.e. which modules have already been through proposal. This is the
    completion record for incremental re-runs, derived from data already
    written (every proposed/approved skill carries its module_ref), so there's
    no separate tracking table to keep in sync. None is a real member here:
    course-root content with no enclosing folder is tracked like any module,
    so it's proposed once and then skipped, not re-run every time."""
    rows = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "select": "module_ref",
    })
    return {r["module_ref"] for r in rows}


def _flag_in_batch_duplicates(items: list[dict]) -> int:
    """Annotate near-duplicate proposals WITHIN a single run, in place.

    items: dicts each carrying at least {"name", "embedding", "dup_note": None}.
    Embeddings are computed once by the caller and reused here, so this adds
    no extra embed calls.

    Deliberate design (matches HITL): in-batch duplicates are FLAGGED, never
    auto-collapsed. Two proposals from the same run are BOTH unvetted;
    auto-picking a winner would be the machine making a review decision a
    human hasn't made yet. Cross-course auto-match stays separate and
    unchanged, there the other side is an already-approved, human-vetted
    skill, so reuse is earned. Unvetted-vs-unvetted always goes to a human.

    Returns the number of proposals that got a dup note (for reporting).
    O(n^2) over one run's proposals (tens of skills), so a plain pairwise
    pass is fine, no clustering infra.
    """
    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            sim = cosine(a["embedding"], b["embedding"])
            if sim >= INBATCH_DUP:
                a["dup_note"] = a["dup_note"] or (
                    f"possible duplicate of '{b['name']}' (this batch, sim {sim:.2f})")
                b["dup_note"] = b["dup_note"] or (
                    f"possible duplicate of '{a['name']}' (this batch, sim {sim:.2f})")
    return sum(1 for it in items if it["dup_note"])


def seed_course_skills(
    *, institution_id: str, course_id: str, content_items: list[dict],
) -> dict:
    """Propose skills for a course, one model call per detected module, and
    reconcile each proposal against the institution's approved catalog.

    INCREMENTAL by module: only processes modules that don't already have
    skills for this course. Safe to call repeatedly, a re-run picks up any
    module that wasn't covered before (a module added mid-term, or one that
    produced nothing on a flaky first run) and skips everything already done.
    This is what lets an instructor press a "refresh skills" button as many
    times as they like: it only ever does the work that's actually new.

    Completion is tracked per module via _already_proposed_modules (derived
    from the module_ref already stored on every skill row, no separate
    tracking table).

    content_items is the raw list from LMSConnector.get_content(), the same
    shape ingest_course() already consumes.

    Returns counts for logging, including modulesProcessed (how many modules
    were newly processed this run) and modulesSkipped (already done). A run
    where everything's already covered returns modulesProcessed=0, which is
    the correct, non-erroring "nothing new to do" outcome.
    Best-effort by contract: the caller must treat a raised exception as
    non-fatal, this must never block a launch.
    """
    by_module = _group_content_by_module(content_items)
    done = _already_proposed_modules(institution_id=institution_id, course_id=course_id)

    pending = {ref: text for ref, text in by_module.items() if ref not in done}
    if not pending:
        return {
            "skipped": True,
            "reason": "all modules already have skills",
            "modulesProcessed": 0,
            "modulesSkipped": len(by_module),
        }

    proposed = auto_approved = flagged = insert_failed = 0
    flagged_in_batch = 0

    for mod_ref, joined_text in pending.items():
        proposals = propose_skills_from_text(course_content=joined_text)

        # Phase 1: embed every proposal in this module once, and resolve its
        # cross-course approved match, before writing anything. Doing this up
        # front is what makes in-batch dedup possible: proposals can be
        # compared to EACH OTHER, not only to already-approved skills. (The
        # embedding is reused for both the dup check and the row write, so
        # this is no extra embed calls vs before.)
        staged = []
        for p in proposals:
            match = _find_approved_match(institution_id=institution_id, name=p["name"])
            emb = bedrock.embed(p["name"], input_type="search_document")
            staged.append({
                "p": p,
                "match": match,
                "sim": float(match["similarity"]) if match else 0.0,
                "embedding": emb,
                "name": p["name"],
                "dup_note": None,
            })

        # Flag near-duplicates within this run (mutates dup_note in place).
        flagged_in_batch += _flag_in_batch_duplicates(staged)

        # Phase 2: write. Cross-course auto-match and per-skill insert
        # resilience are unchanged from before.
        for s in staged:
            p, match, sim, emb = s["p"], s["match"], s["sim"], s["embedding"]
            try:
                if match and sim >= AUTO_MATCH:
                    # Same skill, already vetted elsewhere. Reuse it verbatim
                    # and go straight to approved, pointing at the canonical
                    # origin. Even an auto-match is auditable + reversible:
                    # canonical_skill_id records what it was matched to, and
                    # the review UI can detach it (see review endpoint) so an
                    # instructor can fine-tune it for THIS course.
                    db.insert("skills", [{
                        "institution_id": institution_id, "course_id": course_id,
                        "name": match["name"], "bloom_level": match["bloom_level"],
                        "blueprint_weight": match["blueprint_weight"],
                        "status": "approved",
                        "canonical_skill_id": match["id"],
                        "embedding": emb,
                        "module_ref": mod_ref,
                        "proposed_source": f"auto-matched to '{match['name']}' (sim {sim:.2f})",
                    }])
                    auto_approved += 1
                else:
                    # Novel, or a possible duplicate (of an approved skill
                    # and/or of another proposal in this same batch). Stage
                    # for human review, carrying whichever hint(s) apply.
                    notes = []
                    if match and sim >= REVIEW_HINT:
                        notes.append(f"possible duplicate of approved '{match['name']}' (sim {sim:.2f})")
                        flagged += 1
                    if s["dup_note"]:
                        notes.append(s["dup_note"])
                    source = "; ".join(notes) if notes else mod_ref
                    db.insert("skills", [{
                        "institution_id": institution_id, "course_id": course_id,
                        "name": p["name"], "bloom_level": p["bloom_level"],
                        "blueprint_weight": p["weight"],
                        "status": "proposed",
                        "embedding": emb,
                        "module_ref": mod_ref,
                        "proposed_source": source,
                    }])
                    proposed += 1
            except Exception as exc:
                # A single bad write (timeout on a heavy vector insert, etc.)
                # must not abort the run and discard modules already
                # processed, log it, count it, keep going. The proposal work
                # (model + embed) already succeeded and is cheap to re-attempt
                # on the next refresh, but completed modules are not.
                print(f"skill insert failed for '{p['name']}': {exc}")
                insert_failed += 1

    return {
        "skipped": False,
        "modulesProcessed": len(pending),
        "modulesSkipped": len(by_module) - len(pending),
        "proposed": proposed,
        "auto_approved": auto_approved,
        "flagged_possible_duplicate": flagged,
        "flagged_in_batch_duplicate": flagged_in_batch,
        "insertFailed": insert_failed,
    }
