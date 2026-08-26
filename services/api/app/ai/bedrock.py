"""Model access, dispatched by AI_PROVIDER (see config.py).

Named "bedrock.py" for history: every caller (ai/router.py, ai/rag.py,
ai/skill_proposer.py, learn/items.py, routers/diagnostic.py) imports this
module and calls converse()/embed() with the same signatures regardless of
which provider actually answers. That's deliberate: it's the one place a
provider swap needs to happen, an interim OpenRouter path while this runs
outside the school's AWS org account, real Bedrock model access once it
does, with zero changes anywhere else in the codebase either way.
"""
from __future__ import annotations

import json

import httpx

from app.config import get_settings


def converse(*, model_id: str, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
    s = get_settings()
    if s.ai_provider == "openrouter":
        return _openrouter_converse(model_id=model_id, system=system, messages=messages, max_tokens=max_tokens)
    return _bedrock_converse(model_id=model_id, system=system, messages=messages, max_tokens=max_tokens)


def embed(text: str, *, input_type: str = "search_document") -> list[float]:
    s = get_settings()
    # Embedding provider is independent of chat provider on purpose (see
    # config.py EMBED_PROVIDER docstring) -- chat and embedding reliability
    # turned out to be two separate problems in practice, not one.
    provider = s.embed_provider or s.ai_provider
    if provider == "openai":
        return _openai_embed(text, input_type=input_type)
    if provider == "openrouter":
        return _openrouter_embed(text, input_type=input_type)
    return _bedrock_embed(text, input_type=input_type)


# ---- AWS Bedrock -----------------------------------------------------------

def _bedrock_runtime():
    import boto3  # imported lazily so the openrouter-only path needs no AWS SDK

    s = get_settings()
    return boto3.client("bedrock-runtime", region_name=s.aws_region)


def _bedrock_converse(*, model_id: str, system: str, messages: list[dict], max_tokens: int) -> str:
    resp = _bedrock_runtime().converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    parts = resp["output"]["message"]["content"]
    return "".join(p.get("text", "") for p in parts)


def _bedrock_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    resp = _bedrock_runtime().invoke_model(
        modelId=s.bedrock_embed_model,
        body=json.dumps({"texts": [text], "input_type": input_type}),
    )
    body = json.loads(resp["body"].read())
    return body["embeddings"][0]


# ---- OpenRouter (interim, free-tier) ---------------------------------------

def _openrouter_client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=s.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            # OpenRouter's recommended (optional) app-identification headers.
            "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala",
        },
        timeout=60.0,  # free-tier models can be slow; generous but bounded
    )


def _flatten_text(content) -> str:
    """Every current caller sends messages=[{"role": "user", "content":
    [{"text": "..."}]}] (the Bedrock Converse shape). Extract the text
    regardless of how many parts there are, so this doesn't silently drop
    content if that ever changes."""
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content)


def _openrouter_converse(*, model_id: str, system: str, messages: list[dict], max_tokens: int) -> str:
    oai_messages = [{"role": "system", "content": system}]
    for m in messages:
        oai_messages.append({"role": m["role"], "content": _flatten_text(m["content"])})

    with _openrouter_client() as c:
        r = c.post("/chat/completions", json={
            "model": model_id,
            "messages": oai_messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        })
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"] or ""


def _openrouter_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    with _openrouter_client() as c:
        r = c.post("/embeddings", json={
            "model": s.openrouter_embed_model,
            "input": text,
            "input_type": _to_openrouter_input_type(input_type),
        })
        r.raise_for_status()
        data = r.json()
    raw = data["data"][0]["embedding"]

    # Nemotron 3 Embed 1B natively outputs 2048 dims and the hosted API
    # rejects a "dimensions" request parameter (fixed native output only).
    # NVIDIA's own model card documents that slicing to the first N dims and
    # L2-renormalizing keeps the embedding "highly functional" (Matryoshka-
    # style truncation). Sliced to 1024 here so this matches the existing
    # vector(1024) schema (content_items, skills) with zero migration change,
    # and callers (including the diagnostic ingest's hardcoded 1024 check)
    # are none the wiser about which provider actually answered.
    return _truncate_and_renormalize(raw, dims=1024)


def _truncate_and_renormalize(vec: list[float], *, dims: int) -> list[float]:
    if len(vec) <= dims:
        return vec  # already at or under target; nothing to do
    sliced = vec[:dims]
    norm = sum(x * x for x in sliced) ** 0.5
    if norm == 0:
        return sliced  # degenerate all-zero vector; avoid dividing by zero
    return [x / norm for x in sliced]


# Every caller in this codebase uses Bedrock/Cohere-style input_type values
# ("search_document" for content being indexed, "search_query" for a query
# doing the searching). OpenRouter's NVIDIA embedding endpoint uses different
# vocabulary for the same two concepts ("passage" / "query") and, found via
# live testing, is NOT permissive about it: an unrecognized value 400s, and
# omitting the field entirely 500s. So this must always be mapped, never
# passed through and never omitted, for this specific provider.
_OPENROUTER_INPUT_TYPE = {
    "search_document": "passage",
    "search_query": "query",
}


def _to_openrouter_input_type(input_type: str) -> str:
    try:
        return _OPENROUTER_INPUT_TYPE[input_type]
    except KeyError:
        # Any value outside the two this codebase actually sends is almost
        # certainly a new call site introduced without updating this map.
        # Default to "passage" (content-being-indexed is the more common
        # case) rather than forwarding an unrecognized value that we already
        # know this provider rejects outright.
        return "passage"


# ---- OpenAI (embeddings only, interim path) --------------------------------
# Added after live testing found OpenRouter's free NVIDIA embedding endpoint
# consistently returning 500s (a provider-side outage, not a bug in this
# code, the input_type mapping above is correct and was verified against the
# same endpoint). OpenAI's embeddings API has no query/passage distinction
# (input_type is accepted here only for interface parity with the other two
# providers; it's a no-op), and officially supports requesting a smaller
# output via "dimensions" rather than needing manual truncation.

def _openai_client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=s.openai_base_url,
        headers={
            "Authorization": f"Bearer {s.openai_api_key}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def _openai_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    with _openai_client() as c:
        r = c.post("/embeddings", json={
            "model": s.openai_embed_model,
            "input": text,
            "dimensions": 1024,  # matches vector(1024); OpenAI truncates+renormalizes server-side
        })
        r.raise_for_status()
        data = r.json()
    return data["data"][0]["embedding"]
