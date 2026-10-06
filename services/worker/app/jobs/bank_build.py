"""Deficit-driven MCQ bank builder.

This job is deliberately separate from the legacy item-generation queue.  It
only writes reusable rows with origin=bank and never writes generated_items.set_id.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app import rag
from app.bank_config import (
    ACTIVE_DAYS,
    BACKOFF_MIN,
    BANK_CONCURRENCY,
    CONTEXT_CAP_CHARS,
    ERROR_AFTER,
    GENERATION_VERSION,
    JOB_BUDGET_S,
    LEASE_S,
    LOW_WATER,
    MAX_COMPLETION_TOKENS,
    MCQ_BASE,
    MCQ_BATCH,
    MCQ_MAX,
    MCQ_PER_CHUNK,
    MIN_CHUNK_CHARS,
    MIN_CONTEXT_CHARS,
    MIN_USABLE,
    PER_CALL_CAP_S,
    REPLENISH_STEP,
    SATURATION_DUP_SHARE,
    SATURATION_FAILS,
    SIM_THRESHOLD,
)
from app.config import get_settings
from app.db import supabase as db
from app.item_gen import (
    _BANNED_STEM_PHRASES,
    _MCQ_RESPONSE_FORMAT,
    _MCQ_SYSTEM,
    _validated_mcq,
)

logger = logging.getLogger("kala.worker.bank")

_STOP_429 = threading.Event()


class ThinContextError(RuntimeError):
    """The retrieval window is too small to support a grounded batch."""


class ZeroValidBatchError(RuntimeError):
    """A model batch completed, but every returned item was rejected."""

    def __init__(self, rejection_counts: dict[str, int]):
        super().__init__("zero valid bank items")
        self.rejection_counts = rejection_counts


_ABSOLUTE_WORDS = re.compile(r"\b(always|never|no|none|identical|every|all)\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _stem_hash(stem: str) -> str:
    normalized = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", stem.lower())).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def _jaccard(left: str, right: str) -> float:
    a = set(re.findall(r"[a-z0-9]+", left.lower()))
    b = set(re.findall(r"[a-z0-9]+", right.lower()))
    return len(a & b) / len(a | b) if a and b else 0.0


def _schema() -> dict:
    obj = _MCQ_RESPONSE_FORMAT["json_schema"]["schema"]
    return {
        "type": "json_schema",
        "json_schema": {"name": "study_question_batch_wrapper", "strict": True,
                         "schema": {"type": "object", "properties": {
                             "items": {"type": "array", "minItems": 1, "items": obj}},
                             "required": ["items"], "additionalProperties": False}},
    }


def _content(data: dict) -> str:
    choices = data.get("choices") or []
    return ((choices[0].get("message") or {}).get("content") or "") if choices else ""


def _provider(data: dict) -> str | None:
    metadata = data.get("openrouter_metadata") or {}
    endpoints = ((metadata.get("endpoints") or {}).get("available") or [])
    selected = [row for row in endpoints if row.get("selected")]
    return (selected[0].get("provider") if selected else None) or data.get("provider")


def _usage(data: dict) -> dict[str, Any]:
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "reasoning_tokens": usage.get("reasoning_tokens", details.get("reasoning_tokens")),
        "cost": usage.get("cost", data.get("cost")),
    }


_REJECTION_KEYS = ("schema", "choice_count", "banned_phrase", "absolute_words",
                   "reused_choice_set", "stem_length", "duplicate_hash", "near_duplicate")


def _log_model_call(meta: dict, rejections: dict[str, int] | None = None) -> None:
    counts = rejections or {key: 0 for key in _REJECTION_KEYS}
    logger.info(
        "bank_model_call role=bank course_id=%s skill_id=%s model=%s provider=%s latency_ms=%s max_completion_tokens=%d "
        "finish_reason=%s prompt_tokens=%s completion_tokens=%s reasoning_tokens=%s "
        "reasoning_chars=%s usage_keys=%s cost=%s rejection_schema=%d rejection_choice_count=%d "
        "rejection_banned_phrase=%d rejection_absolute_words=%d rejection_reused_choice_set=%d "
        "rejection_stem_length=%d rejection_duplicate_hash=%d rejection_near_duplicate=%d",
        meta.get("course_id"), meta.get("skill_id"), meta.get("model"), meta.get("provider"), meta.get("latency_ms"), MAX_COMPLETION_TOKENS,
        meta.get("finish_reason"), meta.get("prompt_tokens"), meta.get("completion_tokens"),
        meta.get("reasoning_tokens"), meta.get("reasoning_chars"), meta.get("usage_keys"),
        meta.get("cost"), *(int(counts.get(key) or 0) for key in _REJECTION_KEYS),
    )


def _call_model(*, skill: dict, context: str, do_not_repeat: list[str], remaining: float,
                batch_size: int = MCQ_BATCH) -> tuple[list[dict], dict]:
    if _STOP_429.is_set() or remaining <= PER_CALL_CAP_S:
        raise TimeoutError("bank call cannot fit before invocation deadline")
    settings = get_settings()
    system = _MCQ_SYSTEM + (
        f"\n\nReturn exactly {batch_size} independent MCQs in one JSON object with an `items` array. "
        "Do not repeat any existing live stems or choice sets listed in the user payload. "
        "Every wrong choice must be plausible to an unprepared student, not absurd or obviously false. "
        "Vary the choice sets; do not reuse a complete choice set from the do-not-repeat list."
    )
    user = json.dumps({"skill": skill["name"], "bloom_level": skill.get("bloom_level"),
                       "do_not_repeat": do_not_repeat, "source_material": context})
    payload = {
        "model": settings.openrouter_model_bank,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "reasoning": {"max_tokens": settings.bank_reasoning_max_tokens},
        "response_format": _schema(), "temperature": 0.2,
    }
    started = time.perf_counter()
    status_code = None
    logged = False
    try:
        with httpx.Client(base_url=settings.openrouter_base_url, headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json", "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala bank builder", "X-OpenRouter-Metadata": "enabled",
        }, timeout=min(PER_CALL_CAP_S, max(1.0, remaining - 1.0))) as client:
            response = client.post("/chat/completions", json=payload)
            status_code = response.status_code
            if status_code == 429:
                _STOP_429.set()
            response.raise_for_status()
            data = response.json()
        latency_ms = round((time.perf_counter() - started) * 1000)
        choice = (data.get("choices") or [{}])[0]
        finish_reason = choice.get("finish_reason")
        message = choice.get("message") or {}
        reasoning = message.get("reasoning", data.get("reasoning"))
        reasoning_chars = len(reasoning) if isinstance(reasoning, str) else (len(json.dumps(reasoning)) if reasoning is not None else 0)
        usage_keys = ",".join(sorted((data.get("usage") or {}).keys()))
        usage = _usage(data)
        logged = True
        meta = {"course_id": skill.get("course_id"), "skill_id": skill.get("skill_id") or skill.get("id"),
                "model": settings.openrouter_model_bank, "provider": _provider(data),
                "latency_ms": latency_ms, "finish_reason": finish_reason,
                "prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"],
                "reasoning_tokens": usage["reasoning_tokens"], "reasoning_chars": reasoning_chars,
                "usage_keys": usage_keys, "cost": usage["cost"]}
        if finish_reason != "stop":
            _log_model_call(meta)
            raise RuntimeError(f"non-stop finish_reason={finish_reason}")
        parsed = json.loads(_content(data))
        items = parsed.get("items") if isinstance(parsed, dict) else []
        return [item for item in (items or []) if isinstance(item, dict)], {"status": "success", **usage, "_meta": meta}
    except Exception:
        if not logged:
            elapsed = round((time.perf_counter() - started) * 1000)
            _log_model_call({"course_id": skill.get("course_id"), "skill_id": skill.get("skill_id") or skill.get("id"),
                             "model": get_settings().openrouter_model_bank, "provider": None,
                             "latency_ms": elapsed, "finish_reason": "error",
                             "prompt_tokens": None, "completion_tokens": None,
                             "reasoning_tokens": None, "reasoning_chars": 0,
                             "usage_keys": None, "cost": None})
        raise


def _validated_items(items: list[dict], live_stems: list[str],
                     live_choice_sets: list[set[str]] | None = None) -> tuple[list[dict], dict[str, int], list[str]]:
    accepted: list[dict] = []
    seen = list(live_stems)
    seen_hashes: set[str] = set()
    known_choice_sets = live_choice_sets or []
    counts = {key: 0 for key in _REJECTION_KEYS}
    absolute_examples: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            counts["schema"] += 1
            continue
        prompt = item.get("prompt")
        choices_raw = item.get("choices")
        if not isinstance(prompt, str) or not isinstance(choices_raw, list):
            counts["schema"] += 1
            continue
        if len(choices_raw) != 4 or {c.get("id") for c in choices_raw if isinstance(c, dict)} != {"a", "b", "c", "d"}:
            counts["choice_count"] += 1
            continue
        text_fields = [prompt] + [c.get("label", "") for c in choices_raw if isinstance(c, dict)]
        if any(any(phrase in str(text).lower() for phrase in _BANNED_STEM_PHRASES) for text in text_fields):
            counts["banned_phrase"] += 1
            continue
        if not 20 <= len(prompt.strip()) <= 400:
            counts["stem_length"] += 1
            continue
        correct = item.get("correct_choice_id")
        wrong = [c.get("label", "") for c in choices_raw if isinstance(c, dict) and c.get("id") != correct]
        if sum(bool(_ABSOLUTE_WORDS.search(str(label))) for label in wrong) >= 2:
            counts["absolute_words"] += 1
            absolute_examples.extend(str(label) for label in wrong if _ABSOLUTE_WORDS.search(str(label)))
            continue
        choice_set = {str(c.get("label", "")).strip().lower() for c in choices_raw}
        if choice_set in known_choice_sets:
            counts["reused_choice_set"] += 1
            continue
        try:
            stem, choices, correct, explanation = _validated_mcq(json.dumps(item))
            lowered = stem.lower()
            labels = [str(c["label"]).strip().lower() for c in choices]
            if len(set(labels)) != 4 or any(x in {"all of the above", "none of the above"} for x in labels):
                counts["choice_count"] += 1
                continue
            stem_hash = _stem_hash(stem)
            if stem_hash in seen_hashes:
                counts["duplicate_hash"] += 1
                continue
            if any(_jaccard(stem, old) > 0.8 for old in seen):
                counts["near_duplicate"] += 1
                continue
            accepted.append({"prompt": stem, "choices": choices, "correct_choice_id": correct,
                             "explanation": explanation, "stem_hash": stem_hash})
            seen.append(stem)
            seen_hashes.add(stem_hash)
        except Exception:
            counts["schema"] += 1
            continue
    return accepted, counts, absolute_examples


def _valid_items(items: list[dict], live_stems: list[str]) -> list[dict]:
    return _validated_items(items, live_stems)[0]


def _rotated_window(chunks: list[dict], offset: int) -> list[dict]:
    start = offset % len(chunks)
    ordered = chunks[start:] + chunks[:start]
    kept: list[dict] = []
    length = 0
    for chunk in ordered:
        extra = len(chunk["text"]) + (len("\n---\n") if kept else 0)
        if kept and length + extra > CONTEXT_CAP_CHARS:
            break
        kept.append(chunk)
        length += extra
    return kept or [ordered[0]]


def _context_snapshot(chunks: list[dict], offset: int = 0) -> tuple[list[dict], int]:
    window = _rotated_window(chunks, offset) if chunks else []
    return window, len("\n---\n".join(row["text"] for row in window))


def _context_status(depth: int, chunks: list[dict]) -> tuple[str, str | None, int, int]:
    window, chars = _context_snapshot(chunks)
    if depth > 0 and chars < MIN_CONTEXT_CHARS:
        return "no_material", f"thin: {chars} chars across {len(window)} chunks", chars, len(window)
    return ("building" if depth > 0 else "no_material"), None, chars, len(window)


def _depth(skill: dict, institution_id: str, course_id: str) -> tuple[int, list[dict]]:
    embedding = skill.get("embedding")
    if isinstance(embedding, str):
        embedding = [float(value) for value in embedding.strip("[]").split(",")]
    if not embedding:
        return 0, []
    matches = rag.retrieve_embedding(institution_id=institution_id, course_id=course_id,
                                     query_embedding=embedding, k=30)
    by_id: dict[str, dict] = {}
    for row in matches:
        text = (row.get("chunk_text") or "").strip()
        similarity = float(row.get("similarity") or 0)
        if similarity >= SIM_THRESHOLD and len(text) >= MIN_CHUNK_CHARS and row.get("id"):
            by_id[row["id"]] = {"id": row["id"], "text": text, "similarity": similarity}
    return len(by_id), sorted(by_id.values(), key=lambda x: -x["similarity"])


def _live_items(course_id: str, skill_id: str) -> list[dict]:
    return db.select("generated_items", {"course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}",
        "kind": "eq.practice", "origin": "eq.bank", "retired_at": "is.null",
        "select": "id,prompt,stem_hash,choices", "order": "created_at.desc", "limit": "1000"})


def _target(course_id: str, skill_id: str, depth: int, current: dict | None) -> int:
    base = min(MCQ_BASE, MCQ_PER_CHUNK * depth, MCQ_MAX)
    target = max(base, int((current or {}).get("mcq_target") or 0))
    enrollments = db.select("enrollments", {"course_id": f"eq.{course_id}", "role": "eq.student", "select": "user_id", "limit": "1000"})
    since = _iso(_now() - timedelta(days=ACTIVE_DAYS))
    active = db.select("evidence_events", {"course_id": f"eq.{course_id}", "created_at": f"gte.{since}", "select": "user_id,skill_id", "limit": "5000"})
    enrolled_users = {e["user_id"] for e in enrollments}
    active_users = {
        r["user_id"] for r in active
        if r.get("user_id") in enrolled_users and r.get("skill_id") == skill_id
    }
    if active_users:
        bank_count = len(_live_items(course_id, skill_id))
        for user_id in active_users:
            seen = db.select("item_exposures", {"user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}", "skill_id": f"eq.{skill_id}", "last_tested_at": "not.is.null", "select": "item_id", "limit": "1000"})
            if bank_count - len(seen) < LOW_WATER:
                target = min(MCQ_MAX, target + REPLENISH_STEP)
                break
    return min(target, MCQ_PER_CHUNK * depth, MCQ_MAX)


def _replenish_context(course_id: str) -> dict:
    """Fetch the inputs for all-skill replenish decisions once per course."""
    since = _iso(_now() - timedelta(days=ACTIVE_DAYS))
    enrollments = db.select("enrollments", {
        "course_id": f"eq.{course_id}", "role": "eq.student",
        "select": "user_id", "limit": "1000",
    })
    enrolled = {row["user_id"] for row in enrollments}
    evidence = db.select("evidence_events", {
        "course_id": f"eq.{course_id}", "created_at": f"gte.{since}",
        "select": "user_id,skill_id", "limit": "5000",
    })
    active: dict[str, set[str]] = {}
    for row in evidence:
        user_id, skill_id = row.get("user_id"), row.get("skill_id")
        if user_id in enrolled and skill_id:
            active.setdefault(skill_id, set()).add(user_id)
    exposures = db.select("item_exposures", {
        "course_id": f"eq.{course_id}", "last_tested_at": "not.is.null",
        "select": "user_id,skill_id,item_id", "limit": "10000",
    })
    seen: dict[tuple[str, str], set[str]] = {}
    for row in exposures:
        seen.setdefault((row.get("user_id"), row.get("skill_id")), set()).add(row.get("item_id"))
    items = db.select("generated_items", {
        "course_id": f"eq.{course_id}", "kind": "eq.practice", "origin": "eq.bank",
        "retired_at": "is.null", "select": "id,skill_id", "limit": "10000",
    })
    live_counts: dict[str, int] = {}
    for row in items:
        live_counts[row["skill_id"]] = live_counts.get(row["skill_id"], 0) + 1
    return {"active": active, "seen": seen, "live_counts": live_counts}


def _target_from_context(skill_id: str, depth: int, current: dict | None, context: dict) -> int:
    if (current or {}).get("saturated_at") and int((current or {}).get("saturated_depth") or 0) == depth:
        return int((current or {}).get("mcq_ready") or 0)
    base = min(MCQ_BASE, MCQ_PER_CHUNK * depth, MCQ_MAX)
    target = max(base, int((current or {}).get("mcq_target") or 0))
    active_users = context["active"].get(skill_id, set())
    if any(context["live_counts"].get(skill_id, 0) -
           len(context["seen"].get((user_id, skill_id), set())) < LOW_WATER
           for user_id in active_users):
        target = min(MCQ_MAX, target + REPLENISH_STEP)
    return min(target, MCQ_PER_CHUNK * depth, MCQ_MAX)


def _content_changed(rows: list[dict], updated_at: str | None) -> bool:
    if not updated_at:
        return True
    return any((row.get("created_at") or "") > updated_at or
               (row.get("tag_attempted_at") or "") > updated_at for row in rows)


def _needs_depth_recompute(current: dict | None, content_rows: list[dict]) -> bool:
    """New/approved skills and changed course content need a fresh depth."""
    return (current is None or _content_changed(content_rows, current.get("updated_at")) or
            (current.get("status") == "no_material" and int(current.get("depth") or 0) > 0))


def _upsert_state(skill: dict, *, depth: int, target: int, ready: int, status: str, **extra) -> dict:
    row = {"institution_id": skill["institution_id"], "course_id": skill["course_id"], "skill_id": skill["id"],
           "status": status, "mcq_target": target, "mcq_ready": ready, "depth": depth,
           "updated_at": _iso(_now()), **extra}
    rows = db.upsert("skill_bank_state", [row], on_conflict="course_id,skill_id")
    return rows[0] if rows else row


def _lease(state: dict) -> dict | None:
    now = _now()
    filters = {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}",
               "and": f"(mcq_ready.lt.{state['mcq_target']},or(leased_until.is.null,leased_until.lt.{_iso(now)}),or(next_attempt_at.is.null,next_attempt_at.lte.{_iso(now)}))"}
    rows = db.update("skill_bank_state", filters, {"leased_until": _iso(now + timedelta(seconds=LEASE_S)), "status": "building", "updated_at": _iso(now)})
    return rows[0] if rows else None


def _zero_valid_error(counts: dict[str, int]) -> str:
    return "zero_valid:" + json.dumps(
        {key: int(counts.get(key) or 0) for key in _REJECTION_KEYS},
        sort_keys=True, separators=(",", ":"),
    )


def _previous_zero_valid_counts(error: str | None) -> dict[str, int] | None:
    if not isinstance(error, str) or not error.startswith("zero_valid:"):
        return None
    try:
        parsed = json.loads(error[len("zero_valid:"):])
        return {key: int(parsed.get(key) or 0) for key in _REJECTION_KEYS}
    except (TypeError, ValueError):
        return None


def _record_failure(state: dict, exc: Exception, rejection_counts: dict[str, int] | None = None) -> bool:
    failures = int(state.get("consecutive_failures") or 0) + 1
    if rejection_counts is not None and failures >= SATURATION_FAILS and int(state.get("mcq_ready") or 0) >= MIN_USABLE:
        previous = _previous_zero_valid_counts(state.get("last_error"))
        if previous is not None:
            combined = {key: previous.get(key, 0) + rejection_counts.get(key, 0) for key in _REJECTION_KEYS}
            total = sum(combined.values())
            duplicate_total = sum(combined.get(key, 0) for key in ("duplicate_hash", "near_duplicate", "reused_choice_set"))
            if total and duplicate_total / total >= SATURATION_DUP_SHARE:
                values = {"mcq_target": int(state.get("mcq_ready") or 0), "consecutive_failures": 0,
                          "next_attempt_at": None, "leased_until": None, "last_error": None,
                          "status": "ready", "saturated_at": _iso(_now()),
                          "saturated_depth": int(state.get("depth") or 0), "updated_at": _iso(_now())}
                db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, values)
                state.update(values)
                return True
    delay = BACKOFF_MIN[min(failures - 1, len(BACKOFF_MIN) - 1)]
    error = _zero_valid_error(rejection_counts) if rejection_counts is not None else (str(exc) or type(exc).__name__)
    values = {"consecutive_failures": failures, "next_attempt_at": _iso(_now() + timedelta(minutes=delay)),
              "leased_until": None, "last_error": error, "status": "error" if failures >= ERROR_AFTER else "building", "updated_at": _iso(_now())}
    db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, values)
    state.update(values)
    return False


def _build_one(state: dict, chunks: list[dict], offset: int) -> dict:
    live = _live_items(state["course_id"], state["skill_id"])
    live_stems = [r.get("prompt") or "" for r in live[:30]]
    do_not_repeat = [{"stem": r.get("prompt") or "", "choices": r.get("choices") or []} for r in live[:30]]
    live_choice_sets = [{str(c.get("label", "")).strip().lower() for c in (r.get("choices") or [])} for r in live[:30]]
    window, context_chars = _context_snapshot(chunks, offset)
    context = "\n---\n".join(row["text"] for row in window)
    if context_chars < MIN_CONTEXT_CHARS:
        logger.warning("thin_context course_id=%s skill_id=%s chars=%d min_chars=%d",
                       state["course_id"], state["skill_id"], context_chars, MIN_CONTEXT_CHARS)
        raise ThinContextError(f"context has {context_chars} chars; minimum is {MIN_CONTEXT_CHARS}")
    target = int(state.get("mcq_target") or (len(live) + MCQ_BATCH))
    batch_size = min(MCQ_BATCH, max(0, target - len(live)))
    if batch_size < 1:
        return {"inserted": 0, "returned": 0, "usage": {}}
    items, usage = _call_model(skill=state, context=context, do_not_repeat=do_not_repeat,
                               remaining=state["deadline"] - time.monotonic(), batch_size=batch_size)
    valid, rejection_counts, absolute_examples = _validated_items(items, live_stems, live_choice_sets)
    meta = usage.pop("_meta", None)
    if meta:
        _log_model_call(meta, rejection_counts)
    inserted = 0
    for item in valid:
        try:
            choices = list(item["choices"])
            random.SystemRandom().shuffle(choices)
            created = db.insert("generated_items", [{"institution_id": state["institution_id"], "course_id": state["course_id"], "skill_id": state["skill_id"], "kind": "practice", "bloom_level": state.get("bloom_level"), "prompt": item["prompt"], "choices": choices, "correct_choice_id": item["correct_choice_id"], "explanation": item["explanation"], "origin": "bank", "generation_version": GENERATION_VERSION, "stem_hash": item["stem_hash"], "source_chunk_ids": [c["id"] for c in window]}])
            inserted += len(created)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                continue
            raise
    return {"inserted": inserted, "returned": len(items), "usage": usage,
            "rejection_counts": rejection_counts, "absolute_examples": absolute_examples}


def _pending(states: list[dict], *, excluded_skill_ids: set[str] | None = None) -> list[dict]:
    excluded = excluded_skill_ids or set()
    now = _now()

    def eligible(state: dict) -> bool:
        leased_until = _parse_time(state.get("leased_until")) if state.get("leased_until") else None
        next_attempt_at = _parse_time(state.get("next_attempt_at")) if state.get("next_attempt_at") else None
        return (state.get("status") != "no_material" and
                state.get("skill_id") not in excluded and
                int(state.get("depth") or 0) > 0 and
                int(state.get("mcq_ready") or 0) < int(state.get("mcq_target") or 0) and
                (leased_until is None or leased_until <= now) and
                (next_attempt_at is None or next_attempt_at <= now))

    return sorted((s for s in states if eligible(s)),
                  key=lambda s: (int(s.get("mcq_ready") or 0) >= MIN_USABLE, int(s.get("mcq_ready") or 0)))


def run(*, institution_id: str | None = None, course_id: str | None = None,
        remaining_seconds: float | None = None, chain_depth: int = 0) -> dict:
    started = time.monotonic()
    phases = {"course_select_ms": 0, "replenish_ms": 0, "depth_ms": 0,
              "state_upserts_ms": 0, "other_ms": 0}
    deadline = started + min(JOB_BUDGET_S, remaining_seconds or JOB_BUDGET_S)
    _STOP_429.clear()
    course_params = {"select": "id,institution_id", "limit": "1000"}
    if course_id:
        course_params["id"] = f"eq.{course_id}"
    phase_started = time.perf_counter()
    courses = db.select("courses", course_params)
    phases["course_select_ms"] += round((time.perf_counter() - phase_started) * 1000)
    if institution_id:
        courses = [c for c in courses if c.get("institution_id") == institution_id]
    if course_id:
        courses = [c for c in courses if c.get("id") == course_id]
    all_states: list[dict] = []
    chunks_by_skill: dict[str, list[dict]] = {}
    replenish_by_course: dict[str, dict] = {}
    for course in courses:
        phase_started = time.perf_counter()
        skills = db.select("skills", {"course_id": f"eq.{course['id']}", "institution_id": f"eq.{course['institution_id']}", "status": "eq.approved", "select": "id,name,bloom_level,embedding"})
        existing_states = db.select("skill_bank_state", {
            "course_id": f"eq.{course['id']}", "select": "*", "limit": "1000",
        })
        states_by_skill = {row["skill_id"]: row for row in existing_states}
        replenish = _replenish_context(course["id"])
        phases["replenish_ms"] += round((time.perf_counter() - phase_started) * 1000)
        replenish_by_course[course["id"]] = replenish
        content_rows = db.select("content_items", {
            "course_id": f"eq.{course['id']}", "embedding": "not.is.null",
            "select": "created_at,tag_attempted_at", "limit": "10000",
        })
        for skill in skills:
            skill = {**skill, "course_id": course["id"], "institution_id": course["institution_id"]}
            existing = states_by_skill.get(skill["id"])
            current = existing
            recompute = _needs_depth_recompute(current, content_rows)
            need_chunks = recompute or (current is not None and current.get("status") == "building")
            if need_chunks:
                depth_started = time.perf_counter()
                depth, chunks = _depth(skill, course["institution_id"], course["id"])
                phases["depth_ms"] += round((time.perf_counter() - depth_started) * 1000)
                context_status, thin_error, _, _ = _context_status(depth, chunks)
            else:
                depth = int(current.get("depth") or 0)
                chunks = []
                context_status = current.get("status")
                thin_error = current.get("last_error")
            ready = int(replenish["live_counts"].get(skill["id"], 0))
            target = _target_from_context(skill["id"], depth, current, replenish)
            status = "no_material" if context_status == "no_material" else ("ready" if ready >= target else "building")
            if recompute or current is None or target != int(current.get("mcq_target") or 0) or ready != int(current.get("mcq_ready") or 0) or status != current.get("status"):
                state_started = time.perf_counter()
                saturation_cleared = bool(current and current.get("saturated_at") and int(current.get("saturated_depth") or 0) != depth)
                state = _upsert_state(skill, depth=depth, target=target, ready=ready, status=status,
                                      consecutive_failures=0 if status == "no_material" else (current or {}).get("consecutive_failures", 0),
                                      next_attempt_at=None if status == "no_material" else (current or {}).get("next_attempt_at"),
                                      last_error=thin_error if status == "no_material" and depth > 0 else (None if depth == 0 else (current or {}).get("last_error")),
                                      saturated_at=None if saturation_cleared or depth == 0 else (current or {}).get("saturated_at"),
                                      saturated_depth=None if saturation_cleared or depth == 0 else (current or {}).get("saturated_depth"))
                phases["state_upserts_ms"] += round((time.perf_counter() - state_started) * 1000)
                state["_dirty"] = True
            else:
                state = {**current, **skill}
            state.update(skill, deadline=deadline)
            all_states.append(state)
            if chunks:
                chunks_by_skill[skill["id"]] = chunks
    failed_this_run: set[str] = set()
    pending = _pending(all_states, excluded_skill_ids=failed_this_run)
    calls = successes = failures = inserted = 0
    while pending and time.monotonic() < deadline - PER_CALL_CAP_S and not _STOP_429.is_set():
        claims = []
        for state in pending[:BANK_CONCURRENCY]:
            claimed = _lease(state)
            if claimed:
                claimed = {**state, **claimed}
                claimed["_dirty"] = True
                claims.append(claimed)
        if not claims:
            break
        with ThreadPoolExecutor(max_workers=len(claims)) as pool:
            futures = [pool.submit(_build_one, state, chunks_by_skill[state["skill_id"]], calls + i) for i, state in enumerate(claims)]
            for state, future in zip(claims, futures):
                calls += 1
                try:
                    result = future.result()
                    if result["inserted"] < 1:
                        raise ZeroValidBatchError(result.get("rejection_counts") or {})
                    successes += 1
                    inserted += result["inserted"]
                    success_values = {"consecutive_failures": 0, "last_error": None, "leased_until": None, "updated_at": _iso(_now())}
                    db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, success_values)
                    state.update(success_values)
                except Exception as exc:
                    failures += 1
                    failed_this_run.add(state["skill_id"])
                    logger.exception("bank batch failed course_id=%s skill_id=%s", state["course_id"], state["skill_id"])
                    _record_failure(state, exc, getattr(exc, "rejection_counts", None))
        pending = _pending(all_states, excluded_skill_ids=failed_this_run)
    for state in all_states:
        if not state.get("_dirty"):
            continue
        if state["depth"] == 0 or state.get("status") == "no_material":
            continue
        ready = int(replenish_by_course[state["course_id"]]["live_counts"].get(state["skill_id"], 0)) if state["course_id"] in replenish_by_course else len(_live_items(state["course_id"], state["skill_id"]))
        final_status = "ready" if ready >= state["mcq_target"] else ("error" if int(state.get("consecutive_failures") or 0) >= ERROR_AFTER else "building")
        db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, {"mcq_ready": ready, "status": final_status, "consecutive_failures": 0 if final_status == "ready" else state.get("consecutive_failures", 0), "last_error": None if final_status == "ready" else state.get("last_error"), "leased_until": None, "updated_at": _iso(_now())})
    phases["other_ms"] = max(0, round((time.monotonic() - started) * 1000) - sum(phases.values()))
    return {"courses": len(courses), "skills": len(all_states), "calls": calls, "successes": successes,
            "failures": failures, "inserted": inserted, "remaining": bool(_pending(all_states, excluded_skill_ids=failed_this_run)),
            "rate_limited": _STOP_429.is_set(), "chain_depth": chain_depth,
            "phase_ms": phases, "embedding_calls": 0}
