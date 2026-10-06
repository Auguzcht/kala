"""AI skill proposal with institution-wide dedup and a human-in-the-loop gate.

The worker counterpart is ``services/worker/app/skill_proposer.py``. Keep the
prompt, grounding gates, windowing, overlap bands, and dedup behavior aligned.

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
import logging
from datetime import datetime

from app.ai import bedrock
from app.ai import router as model_router
from app.bank.kick import kick_bank
from app.db import supabase as db
from app.lms.hierarchy import build_folder_paths, module_ref_for

logger = logging.getLogger(__name__)

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
# Same-course overlap is intentionally much lower than institution-wide
# deduplication. It is a reviewer hint only. The AWS101 tuning pass found the
# three genuine overlaps at 0.61+; most pairs from 0.55 to 0.60 are related
# but distinct, so the flag floor is 0.60.
COURSE_OVERLAP = 0.60

# These are deliberately duplicated from services/worker/app/bank_config.py.
# The proposer and bank must make the same groundedness decision.
BANK_SIM_THRESHOLD = 0.544
BANK_MIN_CHUNK_CHARS = 200
BANK_MIN_CONTEXT_CHARS = 1000
BANK_CONTEXT_CAP_CHARS = 12000
MAX_CHARS_PER_MODULE = BANK_CONTEXT_CAP_CHARS

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
    "- category is exactly one of: subject, logistics. Use logistics for "
    "course deliverables, submissions, badges, certification or exam "
    "pathways/readiness, course navigation, onboarding, grading or attendance "
    "policies, and platform/tool setup for the course itself.\n"
    "Return ONLY JSON: {\"skills\": [{\"name\": ..., \"bloom_level\": ..., "
    "\"weight\": ..., \"category\": \"subject\"|\"logistics\"}, ...]}. "
    "No prose, no markdown fences."
)

_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


def _parse_proposals(raw: str) -> list[dict]:
    out, _logistics, _missing_category = _parse_proposals_with_stats(raw)
    return out


def _parse_proposals_with_stats(raw: str) -> tuple[list[dict], int, int]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [], 0, 0
    out: list[dict] = []
    logistics = 0
    missing_category = 0
    for s in data.get("skills", []):
        name = (s.get("name") or "").strip()
        bloom = s.get("bloom_level")
        if not name or bloom not in _BLOOM:
            continue  # drop malformed proposals rather than trust them
        category = s.get("category")
        if category is None:
            category = "subject"
            missing_category += 1
            logger.warning("skill proposal missing category; treating as subject: %s", name)
        if category == "logistics":
            logistics += 1
            logger.info("dropping logistics skill proposal: %s", name)
            continue
        if category != "subject":
            continue
        try:
            weight = float(s.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        weight = max(0.5, min(2.0, weight))
        out.append({"name": name, "bloom_level": bloom, "weight": weight, "category": category})
    if logistics:
        logger.info("dropped %d logistics skill proposal(s)", logistics)
    if missing_category:
        logger.warning("%d skill proposal(s) missing category; treated as subject", missing_category)
    return out, logistics, missing_category


def propose_skills_from_text(*, course_content: str) -> list[dict]:
    """One reasoning-model call, for ONE module's content (see module
    docstring for why this must be per-module, not per-course). Returns
    validated, in-proposal-deduped skill dicts. Pure: no DB writes, easy to
    test."""
    raw = model_router.answer(
        system=_SYSTEM,
        user_text=json.dumps({"module_content": course_content[:MAX_CHARS_PER_MODULE]}),
        escalate=True,  # skill design is worth the reasoning-tier model
    )
    return _parse_proposals(raw)


def _propose_skills_with_stats(*, course_content: str) -> tuple[list[dict], int, int]:
    """Run one window and retain parser-stage counts for operational logs."""
    raw = model_router.answer(
        system=_SYSTEM,
        user_text=json.dumps({"module_content": course_content[:MAX_CHARS_PER_MODULE]}),
        escalate=True,
    )
    return _parse_proposals_with_stats(raw)


def _is_pdf_chunk(row: dict) -> bool:
    return "::" in str(row.get("lms_ref") or "")


def _content_windows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pack qualifying chunks into <=12k windows, capped at four windows."""
    windows: list[dict] = []
    current: list[str] = []
    current_ids: list[str] = []
    current_chars = 0
    omitted: list[dict] = []

    def flush() -> None:
        nonlocal current, current_ids, current_chars
        if current:
            windows.append({"text": "\n---\n".join(current), "chunk_ids": current_ids,
                            "chars": current_chars})
            current, current_ids, current_chars = [], [], 0

    for row in rows:
        text = (row.get("chunk_text") or "").strip()
        remaining = text
        while remaining:
            if len(windows) >= 4:
                omitted.append(row)
                break
            room = BANK_CONTEXT_CAP_CHARS - current_chars - (5 if current else 0)
            if room <= 0:
                flush()
                continue
            part, remaining = remaining[:room], remaining[room:]
            current.append(part)
            current_ids.append(row.get("id"))
            current_chars += len(part) + (5 if len(current) > 1 else 0)
            if remaining:
                flush()
        if len(windows) >= 4 and remaining:
            continue
    flush()
    return windows[:4], omitted


def _stored_content_by_module(*, institution_id: str, course_id: str,
                              content_items: list[dict] | None = None) -> tuple[dict, list[dict]]:
    """Load grounded, embedded content from the persisted ingest corpus.

    The raw LMS tree is intentionally not a fallback: a proposal must be
    grounded in what the worker can later retrieve. PDF chunks are identified
    by the persisted ``lms_ref::filename`` convention used by ingest_walk.
    """
    rows = db.select("content_items", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "embedding": "not.is.null",
        "select": "id,chunk_text,embedding,module_ref,created_at,lms_ref",
        "limit": "10000",
    })
    embedded_rows = [row for row in rows if row.get("embedding") is not None]
    qualifying = [
        row for row in rows
        if row.get("embedding") is not None
        and len((row.get("chunk_text") or "").strip()) >= BANK_MIN_CHUNK_CHARS
    ]
    all_modules = {row.get("module_ref") for row in embedded_rows}
    grouped: dict[str | None, list[dict]] = {}
    for row in qualifying:
        grouped.setdefault(row.get("module_ref"), []).append(row)

    modules: dict[str | None, dict] = {}
    for module_ref in all_modules:
        module_rows = grouped.get(module_ref, [])
        if not module_rows:
            logger.info("no qualifying stored content for module %r; no proposals", module_ref)
            continue
        ordered = sorted(
            module_rows,
            key=lambda row: (_is_pdf_chunk(row), len((row.get("chunk_text") or "").strip())),
            reverse=True,
        )
        windows, left_out = _content_windows(ordered)
        if not windows:
            logger.warning("no qualifying stored content for module %r; no proposals", module_ref)
            continue
        if left_out:
            logger.info(
                "left out %d stored chunks for module %r after four %d-char windows: %s",
                len(left_out), module_ref, BANK_CONTEXT_CAP_CHARS,
                [row.get("id") for row in left_out],
            )
        content_times = [_parse_created_at(row.get("created_at")) for row in module_rows]
        modules[module_ref] = {
            "rows": ordered,
            "windows": windows,
            "text": windows[0]["text"],
            "chars": sum(w["chars"] for w in windows),
            "left_out": left_out,
            "max_created_at": max((t for t in content_times if t), default=None),
        }
    return modules, qualifying


def _group_content_by_module(content_items: list[dict]) -> dict[str | None, str]:
    """Legacy pure grouping helper for LMS-shape unit tests and diagnostics.

    Production proposal calls use _stored_content_by_module above, never this
    raw-description grouping path.
    """
    folder_paths = build_folder_paths(content_items)
    groups: dict[str | None, list[str]] = {}
    for item in content_items:
        body = item.get("body_or_description", "")
        if body:
            ref = module_ref_for(folder_paths.get(item.get("lms_content_id"), []))
            groups.setdefault(ref, []).append(body)
    return {ref: "\n\n".join(texts) for ref, texts in groups.items()}


def _find_approved_match(*, institution_id: str, name: str) -> dict | None:
    """Nearest already-approved skill in the institution, or None."""
    emb = bedrock.embed(name, input_type="search_document")
    return _find_approved_match_with_embedding(institution_id=institution_id, embedding=emb)


def _find_approved_match_with_embedding(*, institution_id: str,
                                        embedding: list[float]) -> dict | None:
    matches = db.rpc("match_skills", {
        "p_institution_id": institution_id,
        "p_query": embedding,
        "p_match_count": 1,
    }) or []
    return matches[0] if matches else None


def _course_skills(*, institution_id: str, course_id: str) -> list[dict]:
    """Return existing approved/proposed skills for same-course overlap hints."""
    return db.select("skills", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "status": "in.(approved,proposed)",
        "select": "name,embedding,status",
    })


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _grounding(*, embedding: list[float], course_chunks: list[dict]) -> tuple[int, int]:
    """Return bank-compatible similarity depth and total grounded chars."""
    depth = 0
    chars = 0
    for row in course_chunks:
        text = (row.get("chunk_text") or "").strip()
        row_embedding = row.get("embedding")
        if isinstance(row_embedding, str):
            row_embedding = json.loads(row_embedding)
        if len(text) < BANK_MIN_CHUNK_CHARS or not row_embedding:
            continue
        if _cosine(embedding, row_embedding) >= BANK_SIM_THRESHOLD:
            depth += 1
            chars += len(text)
    return depth, chars


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _module_skill_created_at(*, institution_id: str, course_id: str) -> dict[str | None, datetime | None]:
    rows = db.select("skills", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "select": "module_ref,created_at",
        "limit": "10000",
    })
    latest: dict[str | None, datetime | None] = {}
    for row in rows:
        when = _parse_created_at(row.get("created_at"))
        if when and (latest.get(row.get("module_ref")) is None or when > latest[row.get("module_ref")]):
            latest[row.get("module_ref")] = when
    return latest


def _module_has_new_content(module: dict, latest_skill_at: datetime | None) -> bool:
    if latest_skill_at is None:
        return True
    newest_content = module.get("max_created_at")
    return bool(newest_content and newest_content > latest_skill_at)


def _find_course_overlap(*, name: str, embedding: list[float], existing: list[dict],
                         staged: list[dict]) -> tuple[str, float] | None:
    candidates = existing + staged
    best = None
    for candidate in candidates:
        candidate_embedding = candidate.get("embedding")
        if isinstance(candidate_embedding, str):
            candidate_embedding = json.loads(candidate_embedding)
        if not candidate_embedding:
            continue
        sim = _cosine(embedding, candidate_embedding)
        if sim >= COURSE_OVERLAP and (best is None or sim > best[1]):
            best = (candidate["name"], sim)
    return best


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
    """Propose skills from persisted, embedded content, one call per module.

    Existing modules are eligible again only when newer stored content exists.
    ``content_items`` remains in the caller contract but is intentionally not
    used as a description fallback.
    """
    modules, course_chunks = _stored_content_by_module(
        institution_id=institution_id, course_id=course_id, content_items=content_items,
    )
    latest_skills = _module_skill_created_at(
        institution_id=institution_id, course_id=course_id,
    )
    pending: dict[str | None, tuple[dict, bool]] = {}
    for ref, module in modules.items():
        covered = ref in latest_skills
        if not covered or _module_has_new_content(module, latest_skills[ref]):
            pending[ref] = (module, covered)
    if not pending:
        return {
            "skipped": True,
            "reason": "no new stored content in uncovered modules",
            "modulesProcessed": 0,
            "modulesSkipped": len(modules),
        }

    proposed = auto_approved = flagged = insert_failed = 0
    flagged_in_batch = ungrounded = overlap_dropped = 0
    existing_course_skills = _course_skills(
        institution_id=institution_id, course_id=course_id,
    )

    for mod_ref, (module, covered) in pending.items():
        module_counts = {
            "raw": 0, "logistics": 0, "ungrounded": 0,
            "overlap": 0, "staged": 0, "thin": 0,
        }
        candidates = []
        for window_index, window in enumerate(module["windows"], start=1):
            proposals, logistics, _missing = _propose_skills_with_stats(
                course_content=window["text"],
            )
            module_counts["raw"] += len(proposals) + logistics
            module_counts["logistics"] += logistics
            logger.info(
                "skill proposal stages module=%r window=%d chunks=%d raw=%d logistics=%d",
                mod_ref, window_index, len(window["chunk_ids"]),
                len(proposals) + logistics, logistics,
            )
            for p in proposals:
                emb = bedrock.embed(p["name"], input_type="search_document")
                match = _find_approved_match_with_embedding(
                    institution_id=institution_id, embedding=emb,
                )
                candidates.append({
                    "p": p,
                    "match": match,
                    "sim": float(match["similarity"]) if match else 0.0,
                    "embedding": emb,
                    "name": p["name"],
                    "dup_note": None,
                    "window": window_index,
                })

        # Phase 1: embed every proposal in this module once, and resolve its
        # cross-course approved match, before writing anything. Doing this up
        # front is what makes in-batch dedup possible: proposals can be
        # compared to EACH OTHER, not only to already-approved skills. (The
        # embedding is reused for both the dup check and the row write, so
        # this is no extra embed calls vs before.)
        # Cross-window in-batch duplicate checking happens before the
        # grounding and same-course gates, so no window can hide a duplicate.
        flagged_in_batch += _flag_in_batch_duplicates(candidates)
        staged = []
        for s in candidates:
            p, emb, match = s["p"], s["embedding"], s["match"]
            depth, context_chars = _grounding(embedding=emb, course_chunks=course_chunks)
            if depth == 0:
                logger.info("ungrounded skill proposal dropped: %s (module %r)", p["name"], mod_ref)
                ungrounded += 1
                module_counts["ungrounded"] += 1
                continue
            s.update({"depth": depth, "context_chars": context_chars,
                      "thin": context_chars < BANK_MIN_CONTEXT_CHARS})
            staged.append(s)

        # Same-course overlap is only a reviewer hint. Existing approved and
        # proposed skills, plus earlier proposals in this batch, are all
        # eligible; institution-wide auto-match/review bands remain separate.
        course_staged = []
        for s in staged:
            overlap = _find_course_overlap(
                name=s["name"], embedding=s["embedding"],
                existing=existing_course_skills, staged=course_staged,
            )
            if overlap and overlap[0] != s["name"]:
                s["course_overlap"] = overlap
            course_staged.append(s)

        # Phase 2: write. Cross-course auto-match and per-skill insert
        # resilience are unchanged from before.
        for s in staged:
            p, match, sim, emb = s["p"], s["match"], s["sim"], s["embedding"]
            try:
                if covered:
                    approved_overlap = _find_course_overlap(
                        name=s["name"], embedding=emb,
                        existing=[x for x in existing_course_skills if x.get("status") == "approved"],
                        staged=[],
                    )
                    if approved_overlap:
                        logger.info(
                            "dropping covered-module overlap proposal %s against %s (sim %.2f)",
                            p["name"], approved_overlap[0], approved_overlap[1],
                        )
                        overlap_dropped += 1
                        module_counts["overlap"] += 1
                        continue
                thin_note = f"thin material: {s['context_chars']} chars" if s["thin"] else None
                module_counts["staged"] += 1
                if s["thin"]:
                    module_counts["thin"] += 1
                if match and sim >= AUTO_MATCH and not s["thin"]:
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
                    existing_course_skills.append({
                        "name": match["name"], "embedding": emb, "status": "approved",
                    })
                    auto_approved += 1
                else:
                    # Novel, or a possible duplicate (of an approved skill
                    # and/or of another proposal in this same batch). Stage
                    # for human review, carrying whichever hint(s) apply.
                    notes = []
                    if thin_note:
                        notes.append(thin_note)
                    if match and sim >= REVIEW_HINT:
                        notes.append(f"possible duplicate of approved '{match['name']}' (sim {sim:.2f})")
                        flagged += 1
                    if s["dup_note"]:
                        notes.append(s["dup_note"])
                    if s.get("course_overlap"):
                        notes.append(
                            f"possible overlap with {s['course_overlap'][0]} "
                            f"(same course, sim {s['course_overlap'][1]:.2f})"
                        )
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
                    existing_course_skills.append({
                        "name": p["name"], "embedding": emb, "status": "proposed",
                    })
                    proposed += 1
            except Exception as exc:
                # A single bad write (timeout on a heavy vector insert, etc.)
                # must not abort the run and discard modules already
                # processed, log it, count it, keep going. The proposal work
                # (model + embed) already succeeded and is cheap to re-attempt
                # on the next refresh, but completed modules are not.
                print(f"skill insert failed for '{p['name']}': {exc}")
                insert_failed += 1

        logger.info(
            "skill proposal stages module=%r raw=%d logistics=%d ungrounded=%d "
            "overlap=%d staged=%d thin=%d",
            mod_ref, module_counts["raw"], module_counts["logistics"],
            module_counts["ungrounded"], module_counts["overlap"],
            module_counts["staged"], module_counts["thin"],
        )

    if auto_approved:
        kick_bank(course_id, "skills_approved")

    return {
        "skipped": False,
        "modulesProcessed": len(pending),
        "modulesSkipped": len(modules) - len(pending),
        "proposed": proposed,
        "auto_approved": auto_approved,
        "flagged_possible_duplicate": flagged,
        "flagged_in_batch_duplicate": flagged_in_batch,
        "insertFailed": insert_failed,
        "ungrounded": ungrounded,
        "overlapDropped": overlap_dropped,
    }
