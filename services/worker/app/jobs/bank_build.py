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


_ABSOLUTE_WORDS = re.compile(r"\b(always|never|no|none|identical|only|every|all)\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


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
        "reasoning": {"effort": settings.bank_reasoning_effort},
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
        logger.info("bank_model_call role=bank model=%s provider=%s latency_ms=%d max_completion_tokens=%d finish_reason=%s prompt_tokens=%s completion_tokens=%s reasoning_tokens=%s reasoning_chars=%d usage_keys=%s cost=%s",
                    settings.openrouter_model_bank, _provider(data), latency_ms, MAX_COMPLETION_TOKENS,
                    finish_reason, usage["prompt_tokens"], usage["completion_tokens"], usage["reasoning_tokens"], reasoning_chars, usage_keys, usage["cost"])
        logged = True
        if finish_reason != "stop":
            raise RuntimeError(f"non-stop finish_reason={finish_reason}")
        parsed = json.loads(_content(data))
        items = parsed.get("items") if isinstance(parsed, dict) else []
        return [item for item in (items or []) if isinstance(item, dict)], {"status": "success", **usage}
    except Exception:
        if not logged:
            elapsed = round((time.perf_counter() - started) * 1000)
            logger.info("bank_model_call role=bank model=%s provider=%s latency_ms=%d max_completion_tokens=%d finish_reason=error prompt_tokens=null completion_tokens=null reasoning_tokens=null cost=null",
                        get_settings().openrouter_model_bank, None, elapsed, MAX_COMPLETION_TOKENS)
        raise


def _valid_items(items: list[dict], live_stems: list[str]) -> list[dict]:
    accepted: list[dict] = []
    seen = list(live_stems)
    for item in items:
        try:
            stem, choices, correct, explanation = _validated_mcq(json.dumps(item))
            lowered = stem.lower()
            if not 20 <= len(stem) <= 400 or any(p in lowered for p in _BANNED_STEM_PHRASES):
                continue
            labels = [str(c["label"]).strip().lower() for c in choices]
            if len(set(labels)) != 4 or any(x in {"all of the above", "none of the above"} for x in labels):
                continue
            wrong = [choice["label"] for choice in choices if choice["id"] != correct]
            if sum(bool(_ABSOLUTE_WORDS.search(label)) for label in wrong) >= 2:
                continue
            if any(_jaccard(stem, old) > 0.8 for old in seen):
                continue
            accepted.append({"prompt": stem, "choices": choices, "correct_choice_id": correct,
                             "explanation": explanation, "stem_hash": _stem_hash(stem)})
            seen.append(stem)
        except Exception:
            continue
    return accepted


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
    matches = rag.retrieve(institution_id=institution_id, course_id=course_id,
                           query=skill["name"], k=30)
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


def _record_failure(state: dict, exc: Exception) -> None:
    failures = int(state.get("consecutive_failures") or 0) + 1
    delay = BACKOFF_MIN[min(failures - 1, len(BACKOFF_MIN) - 1)]
    values = {"consecutive_failures": failures, "next_attempt_at": _iso(_now() + timedelta(minutes=delay)),
              "leased_until": None, "last_error": str(exc) or type(exc).__name__, "status": "error" if failures >= ERROR_AFTER else "building", "updated_at": _iso(_now())}
    db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, values)


def _build_one(state: dict, chunks: list[dict], offset: int) -> dict:
    live = _live_items(state["course_id"], state["skill_id"])
    live_stems = [r.get("prompt") or "" for r in live[:30]]
    do_not_repeat = [{"stem": r.get("prompt") or "", "choices": r.get("choices") or []} for r in live[:30]]
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
    valid = _valid_items(items, live_stems)
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
    return {"inserted": inserted, "returned": len(items), "usage": usage}


def _pending(states: list[dict]) -> list[dict]:
    return sorted((s for s in states if s.get("status") != "no_material" and s["depth"] > 0 and int(s.get("mcq_ready") or 0) < int(s["mcq_target"] or 0)),
                  key=lambda s: (int(s.get("mcq_ready") or 0) >= MIN_USABLE, int(s.get("mcq_ready") or 0)))


def run(*, institution_id: str | None = None, course_id: str | None = None,
        remaining_seconds: float | None = None, chain_depth: int = 0) -> dict:
    started = time.monotonic()
    deadline = started + min(JOB_BUDGET_S, remaining_seconds or JOB_BUDGET_S)
    _STOP_429.clear()
    courses = db.select("courses", {"select": "id,institution_id", "bank_serving": "eq.false", "limit": "1000"})
    if institution_id:
        courses = [c for c in courses if c.get("institution_id") == institution_id]
    if course_id:
        courses = [c for c in courses if c.get("id") == course_id]
    all_states: list[dict] = []
    chunks_by_skill: dict[str, list[dict]] = {}
    for course in courses:
        skills = db.select("skills", {"course_id": f"eq.{course['id']}", "institution_id": f"eq.{course['institution_id']}", "status": "eq.approved", "select": "id,name,bloom_level"})
        for skill in skills:
            skill = {**skill, "course_id": course["id"], "institution_id": course["institution_id"]}
            existing = db.select("skill_bank_state", {"course_id": f"eq.{course['id']}", "skill_id": f"eq.{skill['id']}", "select": "*", "limit": "1"})
            current = existing[0] if existing else None
            depth, chunks = _depth(skill, course["institution_id"], course["id"])
            ready = len(_live_items(course["id"], skill["id"]))
            target = _target(course["id"], skill["id"], depth, current)
            context_status, thin_error, _, _ = _context_status(depth, chunks)
            status = "no_material" if context_status == "no_material" else ("ready" if ready >= target else "building")
            state = _upsert_state(skill, depth=depth, target=target, ready=ready, status=status,
                                  consecutive_failures=0 if status == "no_material" else (current or {}).get("consecutive_failures", 0),
                                  next_attempt_at=None if status == "no_material" else (current or {}).get("next_attempt_at"),
                                  last_error=thin_error if status == "no_material" and depth > 0 else (None if depth == 0 else (current or {}).get("last_error")))
            state.update(skill, deadline=deadline)
            all_states.append(state)
            chunks_by_skill[skill["id"]] = chunks
    pending = _pending(all_states)
    calls = successes = failures = inserted = 0
    while pending and time.monotonic() < deadline - PER_CALL_CAP_S and not _STOP_429.is_set():
        claims = []
        for state in pending[:BANK_CONCURRENCY]:
            claimed = _lease(state)
            if claimed:
                claimed.update(state)
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
                        raise RuntimeError("zero valid bank items")
                    successes += 1
                    inserted += result["inserted"]
                    db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, {"consecutive_failures": 0, "last_error": None, "leased_until": None, "updated_at": _iso(_now())})
                except Exception as exc:
                    failures += 1
                    logger.exception("bank batch failed course_id=%s skill_id=%s", state["course_id"], state["skill_id"])
                    _record_failure(state, exc)
        pending = _pending(all_states)
    for state in all_states:
        if state["depth"] == 0 or state.get("status") == "no_material":
            continue
        ready = len(_live_items(state["course_id"], state["skill_id"]))
        final_status = "ready" if ready >= state["mcq_target"] else ("error" if int(state.get("consecutive_failures") or 0) >= ERROR_AFTER else "building")
        db.update("skill_bank_state", {"course_id": f"eq.{state['course_id']}", "skill_id": f"eq.{state['skill_id']}"}, {"mcq_ready": ready, "status": final_status, "consecutive_failures": 0 if final_status == "ready" else state.get("consecutive_failures", 0), "last_error": None if final_status == "ready" else state.get("last_error"), "leased_until": None, "updated_at": _iso(_now())})
    return {"courses": len(courses), "skills": len(all_states), "calls": calls, "successes": successes,
            "failures": failures, "inserted": inserted, "remaining": bool(_pending(all_states)),
            "rate_limited": _STOP_429.is_set(), "chain_depth": chain_depth}
