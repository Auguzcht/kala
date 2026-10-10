"""Worker-side course skill proposer.

This is a deliberate duplicate of ``services/api/app/ai/skill_proposer.py``;
the worker image only contains its own ``app/`` tree. Keep the two files'\n+
grounding thresholds, prompt, logistics filter, overlap bands, and dedup\n+
behavior in sync. Unlike the API copy, this module is checkpointable: a\n+
module is written only after every window in that module has completed.\n+"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime

import httpx

from app import embed
from app.bank_config import BANK_REASONING_MAX_TOKENS, PER_CALL_CAP_S
from app.config import get_settings
from app.db import supabase as db
from app.model_errors import ModelCallError, error_reason

logger = logging.getLogger("kala.worker.skill_proposer")

AUTO_MATCH = 0.92
REVIEW_HINT = 0.82
# AWS101's 1,081 within-run pairs had p90 0.619; the near-duplicate pairs
# begin at 0.905. A 0.90 cutoff avoids merging the 0.859 database pair, whose
# Bloom levels and assessable tasks differ.
INBATCH_DUP = 0.90
COURSE_OVERLAP = 0.60
SIM_THRESHOLD = 0.544
MIN_CHUNK_CHARS = 200
MIN_CONTEXT_CHARS = 1000
CONTEXT_CAP_CHARS = 12000
SAFETY_MARGIN_S = 5.0

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


def _parse(raw: str) -> tuple[list[dict], list[str]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [], []
    out, logistics = [], []
    for row in data.get("skills", []) if isinstance(data, dict) else []:
        name = str(row.get("name") or "").strip()
        bloom = row.get("bloom_level")
        category = row.get("category", "subject")
        if category == "logistics":
            logistics.append(name or "<unnamed>")
            continue
        if category != "subject" or not name or bloom not in _BLOOM:
            continue
        try:
            weight = max(0.5, min(2.0, float(row.get("weight", 1.0))))
        except (TypeError, ValueError):
            weight = 1.0
        out.append({"name": name, "bloom_level": bloom, "weight": weight})
    return out, logistics


def _model(text: str) -> tuple[list[dict], list[str]]:
    s = get_settings()
    with httpx.Client(base_url=s.openrouter_base_url, headers={
        "Authorization": f"Bearer {s.openrouter_api_key}",
        "Content-Type": "application/json", "HTTP-Referer": "https://kala.mmcm.edu.ph",
        "X-Title": "Kala",
    }, timeout=PER_CALL_CAP_S) as client:
        response = client.post("/chat/completions", json={
            "model": s.openrouter_model_bank,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": json.dumps({"module_content": text})},
            ], "max_completion_tokens": 8192,
            # Match the bank role's supported control. OpenRouter rejects a
            # request that supplies both reasoning.effort and reasoning.max_tokens.
            "reasoning": {"max_tokens": min(BANK_REASONING_MAX_TOKENS, 3072)},
        }, timeout=PER_CALL_CAP_S)
        if not response.is_success:
            reason = error_reason(response, (text,))
            logger.error("model request failed role=proposer status=%d error_body=%s",
                         response.status_code, reason)
            raise ModelCallError(response.status_code, reason)
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


def _cursor_key(course_id: str, ref: str | None) -> str:
    return f"proposer:{course_id}:{ref if ref is not None else '__root__'}"


def _freshness(rows: list[dict]) -> str:
    payload = "\n".join(
        f"{row.get('id')}:{row.get('created_at')}:{hashlib.sha256((row.get('chunk_text') or '').encode()).hexdigest()}"
        for row in rows
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _save_cursor(key: str, completed: int, freshness: str, total_windows: int,
                 last_error: dict | None = None) -> None:
    db.upsert("worker_state", [{"key": key, "value": {
        "windows_completed": completed, "windows_total": total_windows,
        "content_freshness": freshness,
        "last_error": last_error,
    }}], on_conflict="key")


def _proposal_status(course_id: str, status: str, **fields) -> dict:
    key = f"proposal:{course_id}"
    rows = db.select("worker_state", {"key": f"eq.{key}", "select": "value", "limit": "1"})
    value = (rows[0].get("value") or {}) if rows else {}
    value.update({"status": status, "updated_at": datetime.now().astimezone().isoformat(), **fields})
    db.upsert("worker_state", [{"key": key, "value": value}], on_conflict="key")
    return value


def _support(vector: list[float], chunks: list[dict]) -> tuple[int, int]:
    matches = [row for row in chunks if _cosine(vector, row.get("embedding")) >= SIM_THRESHOLD]
    return len(matches), sum(len((row.get("chunk_text") or "").strip()) for row in matches)


def run(*, course_id: str, institution_id: str | None = None,
        remaining_seconds: float = 100.0) -> dict:
    started = time.monotonic()
    if institution_id is None:
        course_rows = db.select("courses", {"id": f"eq.{course_id}", "select": "institution_id", "limit": "1"})
        institution_id = course_rows[0].get("institution_id") if course_rows else None
    if not institution_id:
        raise ValueError(f"course {course_id} has no institution")
    run_state = _proposal_status(course_id, "running")
    run_started_at = run_state.get("queued_at") or run_state.get("started_at")
    if not run_started_at:
        run_started_at = datetime.now().astimezone().isoformat()
    _proposal_status(course_id, "running", started_at=run_started_at)
    modules, chunks = _load(course_id, institution_id)
    existing = _existing(institution_id, course_id)
    same_run = [row for row in existing if row.get("status") == "proposed"
                and (_parse_time(row.get("created_at")) or datetime.fromtimestamp(0).astimezone()) >=
                (_parse_time(run_started_at) or datetime.now().astimezone())]
    latest: dict[str | None, datetime | None] = {}
    for row in existing:
        when = _parse_time(row.get("created_at"))
        ref = row.get("module_ref")
        if when and (latest.get(ref) is None or when > latest[ref]):
            latest[ref] = when
    pending = []
    for ref, module in modules.items():
        newest = max((_parse_time(r.get("created_at")) for r in module["rows"]), default=None)
        key = _cursor_key(course_id, ref)
        saved = db.select("worker_state", {"key": f"eq.{key}", "select": "value", "limit": "1"})
        cursor = (saved[0].get("value") or {}) if saved else {}
        freshness = _freshness(module["rows"])
        same_snapshot = cursor.get("content_freshness") == freshness
        completed_windows = int(cursor.get("windows_completed", 0)) if same_snapshot else 0
        is_complete = same_snapshot and completed_windows >= len(module["windows"])
        if is_complete and cursor.get("windows_total") != len(module["windows"]):
            _save_cursor(key, completed_windows, freshness, len(module["windows"]))
        newer_content = ref not in latest or (newest and latest[ref] and newest > latest[ref])
        if not is_complete and (newer_content or same_snapshot):
            pending.append((ref, module, key, freshness, completed_windows, cursor.get("last_error")))

    processed = proposed = auto_approved = 0
    deferred = False
    budget_exhausted = False
    stored_permanent_error: dict | None = None
    for ref, module, cursor_key, freshness, start_window, prior_error in pending:
        module_complete = True
        for window_index in range(start_window, len(module["windows"])):
            if isinstance(prior_error, dict) and int(prior_error.get("status") or 0) in {400, 401, 403, 404, 422}:
                module_complete = False
                deferred = True
                stored_permanent_error = prior_error
                break
            if isinstance(prior_error, dict) and float(prior_error.get("retry_at") or 0) > datetime.now().astimezone().timestamp():
                module_complete = False
                deferred = True
                break
            # Leave enough Lambda time for a full model call plus cleanup and
            # the async continuation invoke. The cursor is already durable.
            if min(remaining_seconds, 100.0) - (time.monotonic() - started) < PER_CALL_CAP_S + SAFETY_MARGIN_S:
                module_complete = False
                budget_exhausted = True
                break
            window = module["windows"][window_index]
            try:
                call_started = time.monotonic()
                proposals, logistics = _model(window["text"])
                call_ms = round((time.monotonic() - call_started) * 1000)
                logger.info("skill proposal stages course_id=%s module=%s window=%d latency_ms=%d logistics=%d raw=%d",
                            course_id, ref, window_index + 1, call_ms, len(logistics), len(proposals) + len(logistics))
                for dropped_name in logistics:
                    logger.info("skill proposal dropped name=%s reason=logistics", dropped_name)
                candidates = []
                for proposal in proposals:
                    vector = embed.embed(proposal["name"], input_type="search_document")
                    candidates.append({"p": proposal, "embedding": vector,
                                       "match": _match(institution_id, vector), "dup_note": None})
                staged = []
                for candidate in candidates:
                    depth, context_chars = _support(candidate["embedding"], chunks)
                    if depth:
                        candidate["depth"], candidate["context_chars"] = depth, context_chars
                        staged.append(candidate)
                    else:
                        logger.info("skill proposal dropped name=%s reason=ungrounded", candidate["p"]["name"])
                # Merge near-duplicates within this output before any write.
                clusters: list[list[dict]] = []
                for candidate in staged:
                    match_cluster = next((group for group in clusters if any(
                        _cosine(candidate["embedding"], old["embedding"]) >= INBATCH_DUP for old in group
                    )), None)
                    if match_cluster is None:
                        clusters.append([candidate])
                    else:
                        match_cluster.append(candidate)
                staged = []
                for group in clusters:
                    keeper = max(group, key=lambda x: (x["context_chars"], x["depth"], len(x["p"]["name"])))
                    if len(group) > 1:
                        keeper["merged_count"] = len(group)
                        for dropped in group:
                            if dropped is keeper:
                                continue
                            logger.info("skill proposal dropped name=%s reason=deduped keeper=%s", dropped["p"]["name"], keeper["p"]["name"])
                    staged.append(keeper)
                window_rows = []
                for candidate in staged:
                    p, match = candidate["p"], candidate["match"]
                    previous = next((row for row in same_run if row.get("embedding") and
                                     _cosine(candidate["embedding"], row["embedding"]) >= INBATCH_DUP), None)
                    if previous:
                        old_depth, old_chars = _support(previous["embedding"], chunks)
                        old_count = 1
                        for part in str(previous.get("proposed_source") or "").split(";"):
                            if part.strip().startswith("merged_count="):
                                try: old_count = int(part.strip().split("=", 1)[1])
                                except ValueError: pass
                        merged_count = old_count + int(candidate.get("merged_count", 1))
                        if (candidate["context_chars"], candidate["depth"]) > (old_chars, old_depth):
                            source = str(ref)
                            if candidate["context_chars"] < MIN_CONTEXT_CHARS:
                                source += f"; thin material: {candidate['context_chars']} chars"
                            source += f"; merged_count={merged_count}"
                            db.update("skills", {"id": f"eq.{previous['id']}"}, {
                                "name": p["name"], "embedding": candidate["embedding"],
                                "bloom_level": p["bloom_level"], "module_ref": ref,
                                "proposed_source": source,
                            })
                            previous.update({"name": p["name"], "embedding": candidate["embedding"],
                                             "bloom_level": p["bloom_level"], "module_ref": ref,
                                             "proposed_source": source})
                            logger.info("skill proposal dropped name=%s reason=deduped keeper=%s", previous.get("name"), p["name"])
                        else:
                            source = str(previous.get("proposed_source") or "")
                            source = "; ".join(x for x in source.split(";") if not x.strip().startswith("merged_count="))
                            source = f"{source}; merged_count={merged_count}".strip("; ")
                            db.update("skills", {"id": f"eq.{previous['id']}"}, {"proposed_source": source})
                            previous["proposed_source"] = source
                            logger.info("skill proposal dropped name=%s reason=deduped keeper=%s", p["name"], previous.get("name"))
                        continue
                    sim = float(match.get("similarity") or 0.0) if match else 0.0
                    same_course = max((_cosine(candidate["embedding"], e.get("embedding"))
                                       for e in existing if e.get("embedding")), default=0.0)
                    if match and sim >= AUTO_MATCH and candidate["context_chars"] >= MIN_CONTEXT_CHARS:
                        row = {"institution_id": institution_id, "course_id": course_id,
                            "name": match["name"], "bloom_level": match["bloom_level"],
                            "blueprint_weight": match["blueprint_weight"], "status": "approved",
                            "canonical_skill_id": match["id"], "embedding": candidate["embedding"],
                            "module_ref": ref, "proposed_source": f"auto-matched to '{match['name']}' (sim {sim:.2f})"}
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
                        source = "; ".join(notes) or str(ref)
                        if candidate.get("merged_count"):
                            source += f"; merged_count={candidate['merged_count']}"
                        row = {"institution_id": institution_id, "course_id": course_id,
                            "name": p["name"], "bloom_level": p["bloom_level"],
                            "blueprint_weight": p.get("weight", 1.0), "status": "proposed",
                            "embedding": candidate["embedding"], "module_ref": ref,
                            "proposed_source": source}
                    window_rows.append(row)
                if window_rows:
                    inserted = db.insert("skills", window_rows)
                    proposed += sum(row["status"] == "proposed" for row in window_rows)
                    auto_approved += sum(row["status"] == "approved" for row in window_rows)
                    # Later windows see earlier persisted-window proposals for
                    # the 0.60 same-course overlap hint.
                    persisted = inserted or window_rows
                    existing.extend(persisted)
                    same_run.extend(row for row in persisted if row.get("status") == "proposed")
                _save_cursor(cursor_key, window_index + 1, freshness, len(module["windows"]))
                prior_error = None
            except ModelCallError as exc:
                retry_count = 1
                saved = db.select("worker_state", {"key": f"eq.{cursor_key}", "select": "value", "limit": "1"})
                prior = (saved[0].get("value") or {}).get("last_error") if saved else None
                if isinstance(prior, dict) and prior.get("status") == exc.status_code:
                    retry_count = int(prior.get("attempts") or 0) + 1
                delay_minutes = min(30, 2 ** min(retry_count - 1, 5))
                retry_at = datetime.now().astimezone().timestamp() + delay_minutes * 60
                _save_cursor(cursor_key, window_index, freshness, len(module["windows"]), {
                    "status": exc.status_code, "reason": exc.reason, "attempts": retry_count,
                    "retry_at": retry_at,
                })
                if exc.permanent:
                    _proposal_status(course_id, "failed", last_error={"status": exc.status_code, "reason": exc.reason})
                    logger.error("skill proposer stopped course_id=%s module=%s window=%d reason=permanent_error status=%d detail=%s",
                                 course_id, ref, window_index + 1, exc.status_code, exc.reason)
                    return {"courseId": course_id, "modulesProcessed": processed,
                            "modulesRemaining": len(pending) - processed, "remaining": False,
                            "permanent_error": True, "stop_reason": "permanent_error",
                            "error_status": exc.status_code, "error_reason": exc.reason,
                            "proposed": proposed, "auto_approved": auto_approved}
                if exc.throttled:
                    logger.warning("skill proposer stopped course_id=%s module=%s window=%d reason=throttle status=%d detail=%s",
                                   course_id, ref, window_index + 1, exc.status_code, exc.reason)
                    return {"courseId": course_id, "modulesProcessed": processed,
                            "modulesRemaining": len(pending) - processed, "remaining": True,
                            "rate_limited": True, "stop_reason": "throttle",
                            "error_status": exc.status_code, "error_reason": exc.reason,
                            "proposed": proposed, "auto_approved": auto_approved}
                logger.warning("skill proposer deferred course_id=%s module=%s window=%d reason=transient_backoff status=%d retry_minutes=%d detail=%s",
                               course_id, ref, window_index + 1, exc.status_code, delay_minutes, exc.reason)
                return {"courseId": course_id, "modulesProcessed": processed,
                        "modulesRemaining": len(pending) - processed, "remaining": True,
                        "retry_deferred": True, "stop_reason": "transient_backoff",
                        "error_status": exc.status_code, "error_reason": exc.reason,
                        "proposed": proposed, "auto_approved": auto_approved}
            except Exception as exc:  # noqa: BLE001 — resume at last committed window
                logger.warning("skill proposal window deferred course_id=%s module=%s window=%d error=%s",
                               course_id, ref, window_index + 1, exc)
                module_complete = False
                break
        if module_complete:
            processed += 1
    remaining = len(pending) - processed
    if stored_permanent_error:
        _proposal_status(course_id, "failed", last_error=stored_permanent_error)
        return {"courseId": course_id, "modulesProcessed": processed, "modulesRemaining": remaining,
                "remaining": False, "permanent_error": True, "stop_reason": "permanent_error",
                "error_status": stored_permanent_error.get("status"),
                "error_reason": stored_permanent_error.get("reason"),
                "proposed": proposed, "auto_approved": auto_approved}
    if deferred and remaining:
        logger.info("skill proposer stopped course_id=%s reason=transient_backoff", course_id)
        return {"courseId": course_id, "modulesProcessed": processed, "modulesRemaining": remaining,
                "remaining": True, "retry_deferred": True, "stop_reason": "transient_backoff",
                "proposed": proposed, "auto_approved": auto_approved}
    if budget_exhausted and remaining:
        logger.info("skill proposer stopped course_id=%s reason=budget", course_id)
    if remaining == 0:
        db.update("courses", {"id": f"eq.{course_id}"}, {"last_skill_seed_at": datetime.now().astimezone().isoformat()})
        _proposal_status(course_id, "done", last_error=None)
    return {"courseId": course_id, "modulesProcessed": processed, "modulesRemaining": remaining,
            "remaining": remaining > 0, "budget_exhausted": budget_exhausted,
            "stop_reason": "budget" if budget_exhausted and remaining else ("done" if remaining == 0 else None),
            "proposed": proposed, "auto_approved": auto_approved}
