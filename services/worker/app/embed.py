"""Embedding access for the worker's backfill job. Deliberate trimmed
duplicate of services/api/app/ai/bedrock.py: same provider dispatch
(bedrock / openrouter / openai) and the same truncate-and-renormalize
handling for OpenRouter's 2048-dim model, but embed() only — the worker
never calls converse(), so that half of bedrock.py isn't reproduced here.

Keep this in sync with services/api/app/ai/bedrock.py's embed() path if
that ever changes (new provider, new dimension, new input_type mapping).
"""
from __future__ import annotations

import json

import httpx

from app.config import get_settings


def embed(text: str, *, input_type: str = "search_document") -> list[float]:
    s = get_settings()
    provider = s.embed_provider or s.ai_provider
    if provider == "openai":
        return _openai_embed(text)
    if provider == "openrouter":
        return _openrouter_embed(text, input_type=input_type)
    return _bedrock_embed(text, input_type=input_type)


def _bedrock_embed(text: str, *, input_type: str) -> list[float]:
    import boto3  # imported lazily so the openrouter/openai-only path needs no AWS SDK

    s = get_settings()
    client = boto3.client("bedrock-runtime", region_name=s.aws_region)
    resp = client.invoke_model(
        modelId=s.bedrock_embed_model,
        body=json.dumps({"texts": [text], "input_type": input_type}),
    )
    body = json.loads(resp["body"].read())
    embeddings = body["embeddings"]
    vectors = next(iter(embeddings.values())) if isinstance(embeddings, dict) else embeddings
    return vectors[0]


_OPENROUTER_INPUT_TYPE = {"search_document": "passage", "search_query": "query"}


def _openrouter_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    with httpx.Client(
        base_url=s.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala",
        },
        timeout=60.0,
    ) as c:
        r = c.post("/embeddings", json={
            "model": s.openrouter_embed_model,
            "input": text,
            "input_type": _OPENROUTER_INPUT_TYPE.get(input_type, "passage"),
        })
        r.raise_for_status()
        data = r.json()
    raw = data["data"][0]["embedding"]
    return _truncate_and_renormalize(raw, dims=1024)


def _truncate_and_renormalize(vec: list[float], *, dims: int) -> list[float]:
    if len(vec) <= dims:
        return vec
    sliced = vec[:dims]
    norm = sum(x * x for x in sliced) ** 0.5
    if norm == 0:
        return sliced
    return [x / norm for x in sliced]


def _openai_embed(text: str) -> list[float]:
    s = get_settings()
    with httpx.Client(
        base_url=s.openai_base_url,
        headers={
            "Authorization": f"Bearer {s.openai_api_key}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    ) as c:
        r = c.post("/embeddings", json={
            "model": s.openai_embed_model,
            "input": text,
            "dimensions": 1024,
        })
        r.raise_for_status()
        data = r.json()
    return data["data"][0]["embedding"]
