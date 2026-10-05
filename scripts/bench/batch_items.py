#!/usr/bin/env python3
"""Read-only AWS101 retrieval and batched-MCQ benchmark.

This script deliberately imports the production prompt/schema/validator, but
never calls a production generation function and never writes to Supabase.
Only benchmark JSON and Markdown artifacts are written under scripts/bench/out
and docs/bugs.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.ai import bedrock  # noqa: E402
from app.ai import rag  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import supabase as db  # noqa: E402
from app.learn.items import (  # noqa: E402
    _BANNED_STEM_PHRASES,
    _MCQ_RESPONSE_FORMAT,
    _MCQ_SYSTEM,
    _validated_mcq,
)

COURSE_ID = "ae4e7680-f94b-4652-b3f6-b9c32f4420de"
MODEL_ID = "deepseek/deepseek-v4.1-flash:floor"
MAX_CONTEXT_CHARS = 12000
TOP_K = 20
MIN_CHUNK_CHARS = 200


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(left: str, right: str) -> float:
    a, b = _token_set(left), _token_set(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _similarity_stats(values: list[float]) -> dict[str, float | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p05": _percentile(values, 0.05),
        "p25": _percentile(values, 0.25),
        "median": statistics.median(values) if values else None,
        "p75": _percentile(values, 0.75),
        "p95": _percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def _choose_threshold(results: list[dict]) -> dict[str, Any]:
    labeled = [r for r in results if r["skill_id"] == r["target_skill_id"] or r["skill_id"] is not None]
    scores = sorted({round(float(r["similarity"]), 6) for r in labeled})
    candidates = sorted({0.0, 1.0, *scores})
    best: tuple[float, float, float, int] | None = None
    for threshold in candidates:
        positives = [r for r in labeled if r["skill_id"] == r["target_skill_id"]]
        negatives = [r for r in labeled if r["skill_id"] != r["target_skill_id"]]
        tp = sum(float(r["similarity"]) >= threshold for r in positives)
        fn = len(positives) - tp
        fp = sum(float(r["similarity"]) >= threshold for r in negatives)
        tn = len(negatives) - fp
        tpr = tp / len(positives) if positives else 0.0
        fpr = fp / len(negatives) if negatives else 0.0
        youden = tpr - fpr
        balanced = ((tp / (tp + fn)) + (tn / (tn + fp))) / 2 if positives and negatives else 0.0
        # Prefer the lowest threshold among tied scores to retain recall.
        candidate = (youden, balanced, -threshold, len(positives))
        if best is None or candidate > best:
            best = candidate
    threshold = -best[2] if best else 0.75
    return {"threshold": threshold, "method": "max Youden J over same-skill vs different-skill labels"}


def _retrieve_skill(skill: dict, institution_id: str) -> dict[str, Any]:
    tagged = db.select("content_items", {
        "course_id": f"eq.{COURSE_ID}",
        "skill_id": f"eq.{skill['id']}",
        "select": "id,skill_id,chunk_text",
        "limit": "1000",
    })
    matches = rag.retrieve(
        institution_id=institution_id,
        course_id=COURSE_ID,
        query=skill["name"],
        k=TOP_K,
    )
    normalized = []
    for match in matches:
        normalized.append({
            "id": match.get("id"),
            "skill_id": match.get("skill_id"),
            "target_skill_id": skill["id"],
            "similarity": float(match.get("similarity") or 0.0),
            "chunk_text": (match.get("chunk_text") or "").strip(),
        })
    return {
        "skill": {"id": skill["id"], "name": skill["name"], "bloom_level": skill.get("bloom_level")},
        "tagged_rows": tagged,
        "matches": normalized,
    }


def _union_chunks(retrieval: dict[str, Any], threshold: float) -> list[dict[str, Any]]:
    target = retrieval["skill"]["id"]
    by_id: dict[str, dict[str, Any]] = {}
    for row in retrieval["tagged_rows"]:
        if len((row.get("chunk_text") or "").strip()) >= MIN_CHUNK_CHARS:
            by_id[row["id"]] = {
                "id": row["id"], "skill_id": row.get("skill_id"),
                "similarity": None, "chunk_text": row["chunk_text"].strip(),
            }
    for row in retrieval["matches"]:
        if row["similarity"] >= threshold and len(row["chunk_text"]) >= MIN_CHUNK_CHARS:
            by_id.setdefault(row["id"], row)
    return list(by_id.values())


def _array_schema() -> dict:
    object_schema = _MCQ_RESPONSE_FORMAT["json_schema"]["schema"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "study_question_batch",
            "strict": True,
            "schema": {"type": "array", "minItems": 1, "items": object_schema},
        },
    }


def _wrapper_schema() -> dict:
    object_schema = _MCQ_RESPONSE_FORMAT["json_schema"]["schema"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "study_question_batch_wrapper",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"items": {"type": "array", "minItems": 1, "items": object_schema}},
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    }


def _post_openrouter(messages: list[dict], max_tokens: int, response_format: dict,
                     variant: dict[str, Any] | None = None) -> dict:
    settings = get_settings()
    variant = variant or {}
    payload: dict[str, Any] = {
        "model": variant.get("model", MODEL_ID),
        "messages": messages,
        # OpenRouter's current API docs prefer max_completion_tokens;
        # max_tokens is deprecated but equivalent for this benchmark cap.
        "max_completion_tokens": max_tokens,
        "temperature": 0.2,
        "response_format": response_format,
    }
    if variant.get("reasoning") is not None:
        payload["reasoning"] = variant["reasoning"]
    if variant.get("provider_mode") == "configured":
        order = [p.strip() for p in (settings.openrouter_provider_order or "").split(",") if p.strip()]
        if order:
            payload["provider"] = {"order": order, "allow_fallbacks": True}
    with httpx.Client(
        base_url=settings.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala batch benchmark",
            "X-OpenRouter-Metadata": "enabled",
        },
        timeout=120.0,
    ) as client:
        response = client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()


def _usage(data: dict) -> dict[str, int | None]:
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "reasoning_tokens": usage.get("reasoning_tokens", details.get("reasoning_tokens")),
    }


def _content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def _extract_items(raw: str) -> list[dict]:
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return [x for x in parsed["items"] if isinstance(x, dict)]
    return []


def _run_batch(skill: dict, chunks: list[dict], context_offset: int, batch_size: int,
               max_tokens: int, response_format: dict, schema_mode: str,
               variant: dict[str, Any] | None = None) -> dict[str, Any]:
    ordered = chunks[context_offset % len(chunks):] + chunks[:context_offset % len(chunks)]
    context = "\n---\n".join(c["chunk_text"] for c in ordered)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS]
    system = _MCQ_SYSTEM + (
        f"\n\nFor this batch, return exactly {batch_size} independent MCQs in one JSON "
        "response. Return the requested batch schema, not a single object."
    )
    user = json.dumps({
        "skill": skill["name"],
        "bloom_level": skill.get("bloom_level"),
        "source_material": context,
    })
    started = time.perf_counter()
    record: dict[str, Any] = {
        "skill_id": skill["id"], "batch_size": batch_size, "max_tokens": max_tokens,
        "context_offset": context_offset, "schema_mode": schema_mode,
        "variant": (variant or {}).get("name", "legacy"),
    }
    try:
        data = _post_openrouter(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens, response_format, variant,
        )
        record["latency_ms"] = round((time.perf_counter() - started) * 1000)
        choice = (data.get("choices") or [{}])[0]
        record["finish_reason"] = choice.get("finish_reason")
        metadata = data.get("openrouter_metadata") or {}
        endpoints = ((metadata.get("endpoints") or {}).get("available") or [])
        selected = [e for e in endpoints if e.get("selected")]
        record["provider_served"] = (selected[0].get("provider") if selected else None) or data.get("provider")
        record["model_served"] = data.get("model")
        usage = data.get("usage") or {}
        record["cost_usd"] = usage.get("cost", data.get("cost"))
        record["cost_details"] = usage.get("cost_details")
        record.update(_usage(data))
        raw = _content(data)
        items = _extract_items(raw) if raw else []
        valid = 0
        stems: list[str] = []
        for item in items:
            try:
                stem, _, _, _ = _validated_mcq(json.dumps(item))
                valid += 1
                stems.append(stem)
            except Exception:
                if isinstance(item.get("prompt"), str):
                    stems.append(item["prompt"])
        near_pairs = []
        for i, left in enumerate(stems):
            for j in range(i + 1, len(stems)):
                score = _jaccard(left, stems[j])
                if score > 0.8:
                    near_pairs.append({"left_index": i, "right_index": j, "jaccard": round(score, 4)})
        record.update({
            "items_returned": len(items),
            "items_passing_validator": valid,
            "near_duplicate_pairs": near_pairs,
            "duplicate_or_near_duplicate_count": len(near_pairs),
        })
    except httpx.HTTPStatusError as exc:
        record.update({
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error": "http_status", "http_status": exc.response.status_code,
            "items_returned": 0, "items_passing_validator": 0,
        })
    except Exception as exc:  # benchmark records failures without leaking response bodies
        record.update({
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "error": type(exc).__name__, "items_returned": 0, "items_passing_validator": 0,
        })
    return record


def _schema_probe(skill: dict, chunks: list[dict]) -> list[dict[str, Any]]:
    probes = []
    for mode, schema in (("array", _array_schema()), ("wrapper", _wrapper_schema())):
        result = _run_batch(skill, chunks, 0, 5, 4096, schema, mode)
        result["probe"] = True
        probes.append(result)
    return probes


def _concurrent(skill: dict, chunks: list[dict], width: int, schema: dict, mode: str) -> dict[str, Any]:
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(_run_batch, skill, chunks, i, 5, 8192, schema, mode) for i in range(width)]
        for future in as_completed(futures):
            results.append(future.result())
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    return {
        "width": width,
        "wall_time_ms": round((time.perf_counter() - started) * 1000),
        "latency_ms": {"min": min(latencies) if latencies else None, "median": statistics.median(latencies) if latencies else None,
                       "max": max(latencies) if latencies else None},
        "http_429_count": sum(r.get("http_status") == 429 for r in results),
        "error_count": sum("error" in r for r in results),
        "results": results,
    }


def _render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# AWS101 batched MCQ generation benchmark",
        "",
        f"Run: `{result['run_at']}`; course: `{COURSE_ID}`; model: `{MODEL_ID}`.",
        "",
        "This run used the production `_MCQ_SYSTEM`, `_BANNED_STEM_PHRASES`, and `_validated_mcq` imports. It made no database writes and does not include prompts or full chunk text.",
        "",
        "## Retrieval and depth",
        "",
        f"Recommended `SIM_THRESHOLD`: **{result['threshold']['threshold']:.6f}**, selected by maximum Youden J over same-skill versus different-skill labels in the top-20 results.",
        "",
        "| Skill | Tagged chunks | Similarity-union depth | Same-skill matches | Different-skill | Null skill |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["retrieval_summary"]:
        lines.append(f"| {row['name']} | {row['tagged_chunk_count']} | {row['union_depth']} | {row['same_skill']} | {row['different_skill']} | {row['null_skill']} |")
    lines += ["", "### Similarity distribution", "", "| Label | Count | Min | Median | P95 | Max |", "|---|---:|---:|---:|---:|---:|"]
    for label, stats in result["similarity_distribution"].items():
        lines.append(f"| {label} | {stats['count']} | {stats['min']} | {stats['median']} | {stats['p95']} | {stats['max']} |")
    lines += ["", "### Threshold examples", "", "Examples are capped to the first 150 characters as requested.", "", "| Side | Skill | Similarity | Label | Example |", "|---|---|---:|---|---|"]
    for row in result["threshold_examples"]:
        example = row["example"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {row['side']} | {row['skill_name']} | {row['similarity']:.6f} | {row['label']} | {example} |")
    lines += ["", "## Batch generation", "", "| Batch | max_tokens | Runs | Successful runs | p50 latency | p95 latency | Validator pass rate | Avg returned | Near-duplicate batches |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["generation_summary"]:
        lines.append(f"| {row['batch_size']} | {row['max_tokens']} | {row['runs']} | {row['successful_runs']} | {row['p50_latency_ms']} ms | {row['p95_latency_ms']} ms | {row['validator_pass_rate']:.1%} | {row['avg_items_returned']:.2f} | {row['near_duplicate_batches']} |")
    lines += ["", "### Schema probe", "", "| Schema | HTTP accepted | Parsed items | Validator-passing items | Finish reason |", "|---|---|---:|---:|---|"]
    for row in result["schema_probe"]:
        lines.append(f"| {row['schema_mode']} | {'yes' if 'error' not in row else 'no'} | {row.get('items_returned', 0)} | {row.get('items_passing_validator', 0)} | {row.get('finish_reason', '')} |")
    lines += ["", "## Concurrency", "", "| Concurrent calls | Wall time | Latency min / median / max | 429s | Errors |", "|---:|---:|---|---:|---:|"]
    for row in result["concurrency"]:
        spread = row["latency_ms"]
        lines.append(f"| {row['width']} | {row['wall_time_ms']} ms | {spread['min']} / {spread['median']} / {spread['max']} ms | {row['http_429_count']} | {row['error_count']} |")
    lines += ["", "## Verification", "", "- `generated_items.source_chunk_ids` is written by the lesson shell in `services/api/app/learn/lessons.py:255-270`; the item generators at `services/api/app/learn/items.py:390-403` and `services/worker/app/item_gen.py:292-306` do not populate it.", "- The flashcard deck query does **not** filter `generated_items.kind`; `services/api/app/routers/flashcards.py:100-104` and `:169-173` filter by item IDs only.", ""]
    for row in result["in_progress_jobs"]:
        lines.append(f"- In-progress practice job `{row['id']}`: started `{row.get('started_at')}`, updated `{row.get('updated_at')}`, age `{row['age_seconds']}s`, stale={row['stale']}.")
    lines += ["", "## Recommendations", "", f"- `SIM_THRESHOLD`: **{result['threshold']['threshold']:.6f}**, based on the measured labeled separation above.", "- `MCQ_BATCH`: **5**; batch-8 results are included for comparison, but use 5 if pass rate or latency degrades.", "- `max_tokens`: choose the smallest budget whose p95 is acceptable and finish reasons are not `length`; see the table above.", "- `BANK_CONCURRENCY`: start at **2** unless the 4-way run has no 429s/errors and its wall time remains within the worker budget.", "- Build-time estimates use the measured successful batch wall time, 2-way concurrency, and the proposed document targets; they are estimates, not production measurements.", ""]
    lines.append(f"- Estimated AWS101 timing: `{json.dumps(result['build_estimate'], sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def _routing_contexts(raw_path: Path) -> tuple[list[dict], dict[str, list[dict]]]:
    """Load the already-measured top-20 retrieval IDs and fetch chunk text only."""
    previous = json.loads(raw_path.read_text())
    selected = previous["selected_skills"]
    top20 = {row["skill_id"]: row for row in previous["retrieval_top20"]}
    ids = [m["content_item_id"] for row in top20.values() for m in row["matches"]
           if m["similarity"] >= 0.544]
    rows = db.select("content_items", {
        "course_id": f"eq.{COURSE_ID}",
        "select": "id,skill_id,chunk_text",
        "limit": "10000",
    })
    by_id = {row["id"]: row for row in rows if row["id"] in set(ids)}
    contexts = {}
    for skill in selected:
        matches = top20[skill["id"]]["matches"]
        chunks = []
        for match in sorted((m for m in matches if m["similarity"] >= 0.544),
                            key=lambda m: (-m["similarity"], m["rank"])):
            row = by_id.get(match["content_item_id"])
            if row and len((row.get("chunk_text") or "").strip()) >= MIN_CHUNK_CHARS:
                chunks.append({"id": row["id"], "skill_id": row.get("skill_id"),
                               "similarity": match["similarity"],
                               "chunk_text": row["chunk_text"].strip()})
        contexts[skill["id"]] = chunks
    return selected, contexts


def _variant_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    returned = sum(r.get("items_returned", 0) for r in rows)
    valid = sum(r.get("items_passing_validator", 0) for r in rows)
    costs = [float(r["cost_usd"]) for r in rows if r.get("cost_usd") is not None]
    reasons = Counter(str(r.get("finish_reason")) for r in rows)
    providers = Counter(str(r.get("provider_served")) for r in rows)
    reasoning = [r.get("reasoning_tokens") for r in rows if r.get("reasoning_tokens") is not None]
    return {
        "runs": len(rows),
        "p50_latency_ms": round(_percentile(latencies, 0.50)) if latencies else None,
        "p95_latency_ms": round(_percentile(latencies, 0.95)) if latencies else None,
        "max_latency_ms": max(latencies) if latencies else None,
        "runs_over_75s": sum(v > 75000 for v in latencies),
        "runs_over_90s": sum(v > 90000 for v in latencies),
        "finish_reason_distribution": dict(reasons),
        "validator_pass_rate": valid / returned if returned else 0.0,
        "items_returned": returned,
        "items_passing_validator": valid,
        "reasoning_tokens_total": sum(reasoning) if reasoning else 0,
        "reasoning_tokens_median": statistics.median(reasoning) if reasoning else None,
        "provider_served": dict(providers),
        "cost_per_batch_usd_mean": statistics.mean(costs) if costs else None,
        "cost_per_batch_usd_total": sum(costs) if costs else None,
        "errors": sum("error" in r for r in rows),
    }


def _render_routing_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# AWS101 item-generation routing benchmark", "",
        f"Run: `{result['run_at']}`; course: `{COURSE_ID}`; schema: `{{items: [...]}}`; batch size: 5; cap: `max_completion_tokens=8192` (the current OpenRouter name for the requested 8192 cap).", "",
        "No production code, migrations, Terraform, or data were changed by the benchmark. Context was read-only similarity matches at SIM_THRESHOLD 0.544, with the existing production prompt, banned phrases, and validator imported.", "",
        "## OpenRouter parameter check", "",
        "The current API documentation names `max_completion_tokens` (and marks `max_tokens` deprecated), `provider` for routing preferences, `reasoning.effort` / `reasoning_effort` for effort, and `reasoning.exclude` for excluding reasoning output. See [OpenRouter chat completions API docs](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion). The benchmark therefore sent `max_completion_tokens: 8192`; the requested `max_tokens=8192` is the same generation cap.", "",
        "## Results", "",
        "| Variant | Model / mode | p50 | p95 | Max | >75s | >90s | Validator pass | Reasoning tokens (total / median) | Provider served | Cost/batch USD | Finish reasons |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for name, row in result["variant_summaries"].items():
        s = row["summary"]
        lines.append(f"| {name} | {row['model']} {row['routing']} {row.get('reasoning_label','')} | {s['p50_latency_ms']} ms | {s['p95_latency_ms']} ms | {s['max_latency_ms']} ms | {s['runs_over_75s']} | {s['runs_over_90s']} | {s['validator_pass_rate']:.1%} ({s['items_passing_validator']}/{s['items_returned']}) | {s['reasoning_tokens_total']} / {s['reasoning_tokens_median']} | `{json.dumps(s['provider_served'], sort_keys=True)}` | {s['cost_per_batch_usd_mean']} | `{json.dumps(s['finish_reason_distribution'], sort_keys=True)}` |")
    lines += ["", "D/E gate: **D and E are flagged if validator pass rate is below 95%; speed is not recommended when that happens.**", "", f"Best B/C by p95: **{result['best_bc']}**. Recommended variant: **{result['recommendation']}**. Recommended p95 under 75 seconds: **{result['recommended_p95_under_75s']}**.", ""]
    return "\n".join(lines)


def run_routing_benchmark(output: Path, markdown: Path, raw_context: Path) -> None:
    selected, contexts = _routing_contexts(raw_context)
    schema = _wrapper_schema()
    base_variants = [
        {"name": "A", "model": "deepseek/deepseek-v4.1-flash:floor", "routing": "floor", "provider_mode": "configured", "reasoning_label": "default"},
        {"name": "B", "model": "deepseek/deepseek-v4.1-flash", "routing": "default", "provider_mode": "default", "reasoning_label": "default"},
        {"name": "C", "model": "deepseek/deepseek-v4.1-flash:nitro", "routing": "nitro", "provider_mode": "default", "reasoning_label": "default"},
    ]
    rows_by_variant: dict[str, list[dict]] = {}
    metadata: dict[str, dict] = {}
    for variant in base_variants:
        rows: list[dict] = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = []
            for i in range(10):
                skill = selected[i % len(selected)]
                futures.append(pool.submit(_run_batch, skill, contexts[skill["id"]], i,
                                           5, 8192, schema, "wrapper", variant))
            for future in as_completed(futures):
                rows.append(future.result())
        rows_by_variant[variant["name"]] = rows
        metadata[variant["name"]] = variant
        print(f"routing_complete variant={variant['name']}", file=sys.stderr, flush=True)

    best_name = min(("B", "C"), key=lambda n: (
        _variant_summary(rows_by_variant[n])["p95_latency_ms"] or float("inf"),
        _variant_summary(rows_by_variant[n])["p50_latency_ms"] or float("inf"),
    ))
    best = metadata[best_name]
    for variant in (
        {**best, "name": "D", "reasoning": {"effort": "low"}, "reasoning_label": "effort=low"},
        {**best, "name": "E", "reasoning": {"exclude": True}, "reasoning_label": "exclude=true"},
    ):
        rows = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = []
            for i in range(10):
                skill = selected[i % len(selected)]
                futures.append(pool.submit(_run_batch, skill, contexts[skill["id"]], i,
                                           5, 8192, schema, "wrapper", variant))
            for future in as_completed(futures):
                rows.append(future.result())
        rows_by_variant[variant["name"]] = rows
        metadata[variant["name"]] = variant
        print(f"routing_complete variant={variant['name']}", file=sys.stderr, flush=True)

    summaries = {}
    for name, rows in rows_by_variant.items():
        summaries[name] = {"model": metadata[name]["model"], "routing": metadata[name]["routing"],
                           "reasoning_label": metadata[name].get("reasoning_label", "default"),
                           "summary": _variant_summary(rows)}
    recommended = min(summaries, key=lambda n: (summaries[n]["summary"]["p95_latency_ms"] or float("inf"),
                                                 summaries[n]["summary"]["p50_latency_ms"] or float("inf")))
    result = {
        "run_at": datetime.now(UTC).isoformat(), "course_id": COURSE_ID,
        "threshold": 0.544, "selected_skills": selected,
        "context_depths": {s["id"]: len(contexts[s["id"]]) for s in selected},
        "variant_summaries": summaries, "variant_runs": rows_by_variant,
        "best_bc": best_name, "recommendation": recommended,
        "recommended_p95_under_75s": (summaries[recommended]["summary"]["p95_latency_ms"] or float("inf")) < 75000,
        "docs_url": "https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(_render_routing_markdown(result))
    print(json.dumps({"raw_json": str(output), "markdown": str(markdown), "recommendation": recommended}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "scripts/bench/out/batch_items.raw.json"))
    parser.add_argument("--markdown", default=str(ROOT / "docs/bugs/batch-generation-benchmark.md"))
    parser.add_argument("--routing-benchmark", action="store_true")
    parser.add_argument("--routing-output", default=str(ROOT / "scripts/bench/out/batch_items_routing.raw.json"))
    parser.add_argument("--routing-markdown", default=str(ROOT / "docs/bugs/batch-generation-routing-benchmark.md"))
    parser.add_argument("--routing-context", default=str(ROOT / "scripts/bench/out/batch_items.raw.json"))
    args = parser.parse_args()

    if args.routing_benchmark:
        run_routing_benchmark(Path(args.routing_output), Path(args.routing_markdown), Path(args.routing_context))
        return

    course = db.select("courses", {"id": f"eq.{COURSE_ID}", "select": "id,institution_id", "limit": "1"})[0]
    skills = db.select("skills", {
        "course_id": f"eq.{COURSE_ID}", "institution_id": f"eq.{course['institution_id']}",
        "status": "eq.approved", "select": "id,name,bloom_level,created_at", "order": "created_at.asc",
    })
    # Keep embedding probes sequential. The configured embedding provider is
    # rate-limited, and parallel probes can turn a fast read-only benchmark
    # into provider throttling before the retrieval distribution is measured.
    retrievals = [
        _retrieve_skill(skill, course["institution_id"])
        for skill in skills
    ]
    print("retrieval_complete", file=sys.stderr, flush=True)
    all_matches = [m for r in retrievals for m in r["matches"]]
    threshold_info = _choose_threshold(all_matches)
    threshold = threshold_info["threshold"]

    retrieval_summary = []
    all_scores: dict[str, list[float]] = {"same_skill": [], "different_skill": [], "null_skill": []}
    examples = []
    for r in retrievals:
        matches = r["matches"]
        for m in matches:
            label = "same_skill" if m["skill_id"] == r["skill"]["id"] else ("null_skill" if m["skill_id"] is None else "different_skill")
            all_scores[label].append(m["similarity"])
        union = _union_chunks(r, threshold)
        counts = Counter("same_skill" if m["skill_id"] == r["skill"]["id"] else ("null_skill" if m["skill_id"] is None else "different_skill") for m in matches)
        retrieval_summary.append({
            "id": r["skill"]["id"], "name": r["skill"]["name"],
            "tagged_chunk_count": sum(len((x.get("chunk_text") or "").strip()) >= MIN_CHUNK_CHARS for x in r["tagged_rows"]),
            "union_depth": len(union), "same_skill": counts["same_skill"],
            "different_skill": counts["different_skill"], "null_skill": counts["null_skill"],
        })
        for side, pool in (("above", [m for m in matches if m["similarity"] >= threshold]),
                           ("below", [m for m in matches if m["similarity"] < threshold])):
            for m in sorted(pool, key=lambda x: abs(x["similarity"] - threshold))[:3]:
                examples.append({
                    "side": side, "skill_name": r["skill"]["name"], "similarity": m["similarity"],
                    "label": "same_skill" if m["skill_id"] == r["skill"]["id"] else ("null_skill" if m["skill_id"] is None else "different_skill"),
                    "example": m["chunk_text"][:150],
                })
    examples = examples[:6]
    retrieval_summary.sort(key=lambda x: (x["union_depth"], x["name"]))
    chosen = [retrieval_summary[0], retrieval_summary[len(retrieval_summary) // 2], retrieval_summary[-1]]
    retrieval_by_id = {r["skill"]["id"]: r for r in retrievals}
    selected_chunks = {row["id"]: _union_chunks(retrieval_by_id[row["id"]], threshold) for row in chosen}

    probe = _schema_probe(retrieval_by_id[chosen[1]["id"]]["skill"], selected_chunks[chosen[1]["id"]])
    working_mode = "array" if "error" not in probe[0] else "wrapper"
    working_schema = _array_schema() if working_mode == "array" else _wrapper_schema()
    print("schema_probe_complete", file=sys.stderr, flush=True)

    generation_runs = []
    for row in chosen:
        skill = retrieval_by_id[row["id"]]["skill"]
        chunks = selected_chunks[row["id"]]
        for batch_size, run_count in ((5, 5), (8, 3)):
            for max_tokens in (4096, 8192) if batch_size == 5 else (8192,):
                with ThreadPoolExecutor(max_workers=run_count) as pool:
                    futures = [pool.submit(_run_batch, skill, chunks, i, batch_size, max_tokens, working_schema, working_mode) for i in range(run_count)]
                    generation_runs.extend(f.result() for f in futures)
                print(f"generation_complete batch={batch_size} max_tokens={max_tokens} skill={skill['id']}", file=sys.stderr, flush=True)

    concurrency = [_concurrent(retrieval_by_id[chosen[-1]["id"]]["skill"], selected_chunks[chosen[-1]["id"]], width, working_schema, working_mode) for width in (2, 4)]
    print("concurrency_complete", file=sys.stderr, flush=True)

    summary = []
    for batch_size, max_tokens in ((5, 4096), (5, 8192), (8, 8192)):
        rows = [r for r in generation_runs if r["batch_size"] == batch_size and r["max_tokens"] == max_tokens]
        latencies = [r["latency_ms"] for r in rows if "latency_ms" in r]
        total_items = sum(r.get("items_returned", 0) for r in rows)
        total_valid = sum(r.get("items_passing_validator", 0) for r in rows)
        summary.append({
            "batch_size": batch_size, "max_tokens": max_tokens, "runs": len(rows),
            "successful_runs": sum("error" not in r for r in rows),
            "p50_latency_ms": round(_percentile(latencies, 0.5)) if latencies else None,
            "p95_latency_ms": round(_percentile(latencies, 0.95)) if latencies else None,
            "validator_pass_rate": total_valid / total_items if total_items else 0.0,
            "avg_items_returned": total_items / len(rows) if rows else 0.0,
            "near_duplicate_batches": sum(bool(r.get("near_duplicate_pairs")) for r in rows),
        })

    jobs = db.select("item_generation_jobs", {
        "course_id": f"eq.{COURSE_ID}", "kind": "eq.practice", "status": "eq.in_progress",
        "select": "id,started_at,updated_at,created_at", "order": "started_at.asc",
    })
    now = datetime.now(UTC)
    in_progress = []
    for job in jobs:
        updated = datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00"))
        age = max(0, int((now - updated).total_seconds()))
        in_progress.append({**job, "age_seconds": age, "stale": age > 150})

    best = next((x for x in summary if x["batch_size"] == 5 and x["max_tokens"] == 8192), None)
    calls_per_skill = 1
    min_usable = 5
    full_target = 80
    total_needed_min = sum(max(0, min_usable - x["union_depth"]) for x in retrieval_summary)
    total_needed_full = sum(max(0, full_target - x["union_depth"]) for x in retrieval_summary)
    batch_wall = (best or {}).get("p95_latency_ms") or 0
    per_batch_seconds = batch_wall / 1000
    build_estimate = {
        "assumptions": "5 MCQs per successful batch, BANK_CONCURRENCY=2, 5-item 8192 p95, target 80 per skill",
        "course_approved_skills": len(retrieval_summary),
        "batches_to_min_usable": math.ceil(total_needed_min / 5) if total_needed_min else 0,
        "seconds_to_min_usable_estimate": round(math.ceil(total_needed_min / 5) * per_batch_seconds / 2, 1),
        "batches_to_full_target": math.ceil(total_needed_full / 5) if total_needed_full else 0,
        "seconds_to_full_target_estimate": round(math.ceil(total_needed_full / 5) * per_batch_seconds / 2, 1),
        "note": "Extrapolation only; actual provider throttling, validation losses, and target reconciliation are excluded.",
    }

    result = {
        "run_at": datetime.now(UTC).isoformat(), "course_id": COURSE_ID, "model": MODEL_ID,
        "threshold": threshold_info, "retrieval_summary": retrieval_summary,
        "similarity_distribution": {k: _similarity_stats(v) for k, v in all_scores.items()},
        "threshold_examples": examples, "selected_skills": chosen,
        "schema_probe": probe, "working_schema_mode": working_mode,
        "generation_runs": generation_runs, "generation_summary": summary,
        "concurrency": concurrency, "in_progress_jobs": in_progress,
        "build_estimate": build_estimate,
        "verification": {
            "source_chunk_ids_writers": ["services/api/app/learn/lessons.py:255-270"],
            "item_generators_populate_source_chunk_ids": False,
            "flashcard_deck_filters_kind": False,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    Path(args.markdown).write_text(_render_markdown(result))
    print(json.dumps({"raw_json": str(output), "markdown": args.markdown, "threshold": threshold, "working_schema": working_mode}, indent=2))


if __name__ == "__main__":
    main()
