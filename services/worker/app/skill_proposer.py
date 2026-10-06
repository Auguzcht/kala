"""Worker-side course skill proposer.

This is a deliberate duplicate of ``services/api/app/ai/skill_proposer.py``;
the worker image only contains its own ``app/`` tree. Keep the two files'\n+
grounding thresholds, prompt, logistics filter, overlap bands, and dedup\n+
behavior in sync. Unlike the API copy, this module is checkpointable: a\n+
module is written only after every window in that module has completed.\n+"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import httpx

from app import embed
from app.config import get_settings
from app.db import supabase as db

logger = logging.getLogger("kala.worker.skill_proposer")

AUTO_MATCH = 0.92
REVIEW_HINT = 0.82
INBATCH_DUP = 0.82
COURSE_OVERLAP = 0.60
SIM_THRESHOLD = 0.544
MIN_CHUNK_CHARS = 200
MIN_CONTEXT_CHARS = 1000
CONTEXT_CAP_CHARS = 12000
MAX_TOKENS = 4096

_BLOOM = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
_SYSTEM = (
    "You extract a small set of CANONICAL, ASSESSABLE skills from ONE module's course content.\n"
    "Each skill must be observable and assessable and start with a cognitive verb.\n"
    "Deduplicate within your output and prefer fewer, high-quality skills.\n"
    "bloom_level must be remember, understand, apply, analyze, evaluate, or create.\n"
    "category is subject or logistics; logistics includes deliverables, badges, certification,\n"
    "exam pathways, navigation, onboarding, grading, attendance, and platform setup.\n"
    "Return ONLY JSON: {\"skills\":[{\"name\":...,\"bloom_level\":...,\"weight\":...,\"category\":\"subject\"|\"logistics\"}]}"
)


def _parse(raw: str) -> tuple[list[dict], int]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [], 0
    out, logistics = [], 0
    for row in data.get("skills", []) if isinstance(data, dict) else []:
        name = str(row.get("name") or "").strip()
        bloom = row.get("bloom_level")
        category = row.get("category", "subject")
        if category == "logistics":
            logistics += 1
            continue
        if category != "subject" or not name or bloom not in _BLOOM:
            continue
        try:
            weight = max(0.5, min(2.0, float(row.get("weight", 1.0))))
        except (TypeError, ValueError):
            weight = 1.0
        out.append({"name": name, "bloom_level": bloom, "weight": weight})
    return out, logistics


def _model(text: str) -> tuple[list[dict], int]:
    s = get_settings()
    with httpx.Client(base_url=s.openrouter_base_url, headers={
        "Authorization": f"Bearer {s.openrouter_api_key}",
        "Content-Type": "application/json", "HTTP-Referer": "https://kala.mmcm.edu.ph",
        "X-Title": "Kala",
    }, timeout=120.0) as client:
        response = client.post("/chat/completions", json={
            "model": getattr(s, "openrouter_model_reasoning", s.openrouter_model_default),
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": json.dumps({"module_content": text})},
            ], "max_tokens": MAX_TOKENS,
        })
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    content = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
    return _parse(content)


def _cosine(a, b) -> float:
    if isinstance(a, str):
        a = json.loads(a)
    if isinstance(b, str):
        b = json.loads(b)
    dot = sum(x * y for x, y in zip(a or [], b or []))
    na = sum(x * x for x in (a or [])) ** 0.5
    nb = sum(y * y for y in (b or [])) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _windows(rows: list[dict]) -> list[dict]:
    windows, current, ids, chars = [], [], [], 0
    for row in rows:
        text = (row.get("chunk_text") or "").strip()
        while text:
            room = CONTEXT_CAP_CHARS - chars - (5 if current else 0)
            if room <= 0:
                windows.append({"text": "\n---\n".join(current), "chunk_ids": ids})
                current, ids, chars = [], [], 0
                continue
            part, text = text[:room], text[room:]
            current.append(part); ids.append(row.get("id")); chars += len(part) + (5 if len(current) > 1 else 0)
            if text:
                windows.append({"text": "\n---\n".join(current), "chunk_ids": ids})
                current, ids, chars = [], [], 0
    if current:
        windows.append({"text": "\n---\n".join(current), "chunk_ids": ids})
    return windows


def _load(course_id: str, institution_id: str | None) -> tuple[dict, list[dict]]:
    params = {"course_id": f"eq.{course_id}", "embedding": "not.is.null",
              "select": "id,chunk_text,embedding,module_ref,created_at,lms_ref", "limit": "10000"}
    if institution_id:
        params["institution_id"] = f"eq.{institution_id}"
    rows = db.select("content_items", params)
    rows = [r for r in rows if len((r.get("chunk_text") or "").strip()) >= MIN_CHUNK_CHARS]
    grouped: dict[str | None, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get("module_ref"), []).append(row)
    return {ref: {"rows": sorted(items, key=lambda r: len(r.get("chunk_text") or ""), reverse=True),
                  "windows": _windows(items)} for ref, items in grouped.items()}, rows


def _existing(institution_id: str | None, course_id: str) -> list[dict]:
    params = {"course_id": f"eq.{course_id}", "status": "in.(approved,proposed)",
              "select": "id,name,embedding,status,module_ref,created_at", "limit": "10000"}
    if institution_id:
        params["institution_id"] = f"eq.{institution_id}"
    return db.select("skills", params)


def _match(institution_id: str | None, vector: list[float]) -> dict | None:
    if not institution_id:
        return None
    rows = db.rpc("match_skills", {"p_institution_id": institution_id, "p_query": vector, "p_match_count": 1}) or []
    return rows[0] if rows else None


def _dedup(items: list[dict]) -> None:
    for i, left in enumerate(items):
        for right in items[i + 1:]:
            if _cosine(left["embedding"], right["embedding"]) >= INBATCH_DUP:
                left["dup_note"] = left.get("dup_note") or f"possible duplicate of '{right['name']}'"
                right["dup_note"] = right.get("dup_note") or f"possible duplicate of '{left['name']}'"


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def run(*, course_id: str, institution_id: str | None = None,
        remaining_seconds: float = 100.0) -> dict:
    started = time.monotonic()
    if institution_id is None:
        course_rows = db.select("courses", {"id": f"eq.{course_id}", "select": "institution_id", "limit": "1"})
        institution_id = course_rows[0].get("institution_id") if course_rows else None
    if not institution_id:
        raise ValueError(f"course {course_id} has no institution")
    modules, chunks = _load(course_id, institution_id)
    existing = _existing(institution_id, course_id)
    latest: dict[str | None, datetime | None] = {}
    for row in existing:
        when = _parse_time(row.get("created_at"))
        ref = row.get("module_ref")
        if when and (latest.get(ref) is None or when > latest[ref]):
            latest[ref] = when
    pending = []
    for ref, module in modules.items():
        newest = max((_parse_time(r.get("created_at")) for r in module["rows"]), default=None)
        if ref not in latest or (newest and latest[ref] and newest > latest[ref]):
            pending.append((ref, module))
    processed = proposed = auto_approved = 0
    for ref, module in pending:
        # Checkpoint only between whole modules. No writes occur until all
        # windows below have returned, so a timeout cannot leave a half module.
        if time.monotonic() - started + 5 >= min(remaining_seconds, 100.0):
            break
        candidates = []
        try:
            for window in module["windows"]:
                proposals, logistics = _model(window["text"])
                logger.info("skill proposal stages course_id=%s module=%s logistics=%d raw=%d",
                            course_id, ref, logistics, len(proposals) + logistics)
                for proposal in proposals:
                    vector = embed.embed(proposal["name"], input_type="search_document")
                    candidates.append({"p": proposal, "embedding": vector,
                                       "match": _match(institution_id, vector), "dup_note": None})
        except Exception as exc:  # noqa: BLE001 — a module is retried as a whole
            logger.warning("skill proposal module deferred course_id=%s module=%s error=%s", course_id, ref, exc)
            break
        _dedup(candidates)
        staged = []
        for candidate in candidates:
            proposal = candidate["p"]
            depth = sum(1 for row in chunks if _cosine(candidate["embedding"], row.get("embedding")) >= SIM_THRESHOLD)
            context_chars = sum(len((row.get("chunk_text") or "").strip()) for row in chunks
                                if _cosine(candidate["embedding"], row.get("embedding")) >= SIM_THRESHOLD)
            if depth == 0:
                continue
            candidate["depth"], candidate["context_chars"] = depth, context_chars
            staged.append(candidate)
        # All writes for this module happen after every window succeeded.
        module_rows = []
        module_proposed = module_auto_approved = 0
        for candidate in staged:
            p, match = candidate["p"], candidate["match"]
            sim = float(match.get("similarity") or 0.0) if match else 0.0
            same_course = max((_cosine(candidate["embedding"], e.get("embedding")) for e in existing if e.get("embedding")), default=0.0)
            if match and sim >= AUTO_MATCH and candidate["context_chars"] >= MIN_CONTEXT_CHARS:
                module_rows.append({"institution_id": institution_id, "course_id": course_id,
                    "name": match["name"], "bloom_level": match["bloom_level"],
                    "blueprint_weight": match["blueprint_weight"], "status": "approved",
                    "canonical_skill_id": match["id"], "embedding": candidate["embedding"], "module_ref": ref,
                    "proposed_source": f"auto-matched to '{match['name']}' (sim {sim:.2f})"})
                module_auto_approved += 1
            else:
                notes = []
                if candidate["context_chars"] < MIN_CONTEXT_CHARS:
                    notes.append(f"thin material: {candidate['context_chars']} chars")
                if match and sim >= REVIEW_HINT:
                    notes.append(f"possible duplicate of approved '{match['name']}' (sim {sim:.2f})")
                if same_course >= COURSE_OVERLAP:
                    notes.append("possible overlap in this course")
                if candidate.get("dup_note"):
                    notes.append(candidate["dup_note"])
                module_rows.append({"institution_id": institution_id, "course_id": course_id,
                    "name": p["name"], "bloom_level": p["bloom_level"],
                    "blueprint_weight": p["weight"], "status": "proposed", "embedding": candidate["embedding"],
                    "module_ref": ref, "proposed_source": "; ".join(notes) or ref})
                module_proposed += 1
        # One bulk write is the module checkpoint. If it fails, nothing from
        # this module is persisted and the next chained run retries the whole
        # module instead of leaving a half-proposed module behind.
        if module_rows:
            db.insert("skills", module_rows)
            proposed += module_proposed
            auto_approved += module_auto_approved
            existing.extend(module_rows)
        processed += 1
    remaining = len(pending) - processed
    if remaining == 0:
        db.update("courses", {"id": f"eq.{course_id}"}, {"last_skill_seed_at": datetime.now().astimezone().isoformat()})
    return {"courseId": course_id, "modulesProcessed": processed, "modulesRemaining": remaining,
            "remaining": remaining > 0, "proposed": proposed, "auto_approved": auto_approved}
