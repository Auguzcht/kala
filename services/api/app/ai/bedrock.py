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
import logging

import httpx

from app.ai.errors import ModelUnavailableError
from app.config import get_settings

logger = logging.getLogger(__name__)


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
    try:
        resp = _bedrock_runtime().converse(
            modelId=model_id,
            system=[{"text": system}],
            messages=messages,
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
        )
    except Exception as exc:  # botocore ClientError, EndpointConnectionError, timeouts…
        # Whether the model id is unknown or Bedrock itself is unreachable,
        # the caller's remedy is the same (retry later / fix config), so this
        # is one typed, non-500 failure rather than a provider-specific throw.
        logger.error("bedrock converse failed (model=%s): %s", model_id, exc)
        raise ModelUnavailableError(
            "The model provider could not be reached. Please try again.",
            provider="bedrock", model_id=model_id,
        ) from exc
    parts = resp["output"]["message"]["content"]
    return "".join(p.get("text", "") for p in parts)


def _bedrock_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    resp = _bedrock_runtime().invoke_model(
        modelId=s.bedrock_embed_model,
        body=json.dumps({"texts": [text], "input_type": input_type}),
    )
    body = json.loads(resp["body"].read())
    embeddings = body["embeddings"]
    # Cohere embed-v4 returns {"float": [[...]]} keyed by dtype (live-verified);
    # the code has always assumed the older flat list [[...]] — handle both by
    # taking the first dtype bucket when the value is a dict.
    vectors = next(iter(embeddings.values())) if isinstance(embeddings, dict) else embeddings
    return vectors[0]


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
        # 20s, not 60s: this client is called synchronously inside
        # user-facing requests (/lti/launch's skill proposal, /skills/propose,
        # tutor, item generation) that run on a 30s Lambda timeout behind an
        # API Gateway HTTP API integration — which hard-caps the wait at 30s
        # regardless of this client's own setting. A 60s timeout here meant
        # a hung free-tier model never raised its own httpx.TimeoutException;
        # the platform killed the whole Lambda first, with no exception for
        # the surrounding try/except (_seed_course_skills) to catch — silent
        # "Service Unavailable" instead of the clean "skipped" behavior that
        # code already has. 20s leaves headroom for whatever else runs in
        # the same request (DB calls, other content) while still firing well
        # before the 30s wall.
        timeout=20.0,
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

    try:
        with _openrouter_client() as c:
            r = c.post("/chat/completions", json={
                "model": model_id,
                "messages": oai_messages,
                "max_tokens": max_tokens,
                "temperature": 0.2,
            })
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        # 404 from OpenRouter means the MODEL ID DOES NOT EXIST, nearly always
        # because a free-tier model was retired upstream. That is a config
        # problem, not an outage, and it is the failure that used to take
        # every AI endpoint down silently — log it loudly and specifically so
        # the next deprecation is caught in the logs before a user reports a
        # broken screen. 401/403 (bad key), 429 (rate limit) and 5xx (provider
        # outage) share the same typed failure but not the same log line.
        model_not_found = status_code == 404
        if model_not_found:
            logger.error(
                "OpenRouter model id no longer exists (model=%s). It was "
                "likely retired from the free tier — set OPENROUTER_MODEL_* "
                "to a current id (see https://openrouter.ai/models). Body: %s",
                model_id, exc.response.text[:300],
            )
        else:
            logger.error(
                "OpenRouter chat request failed (model=%s, status=%s): %s",
                model_id, status_code, exc.response.text[:300],
            )
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openrouter", model_id=model_id,
            status_code=status_code, model_not_found=model_not_found,
        ) from exc
    except httpx.HTTPError as exc:
        # Transport-level failure (timeout, DNS, connection reset) — no
        # response object to read a status from. Same typed failure.
        logger.error("OpenRouter request errored (model=%s): %s", model_id, exc)
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openrouter", model_id=model_id,
        ) from exc
    return data["choices"][0]["message"]["content"] or ""


def _openrouter_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    try:
        with _openrouter_client() as c:
            r = c.post("/embeddings", json={
                "model": s.openrouter_embed_model,
                "input": text,
                "input_type": _to_openrouter_input_type(input_type),
            })
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as exc:
        model_not_found = exc.response.status_code == 404
        logger.error(
            "OpenRouter embedding request failed (model=%s, status=%s%s): %s",
            s.openrouter_embed_model, exc.response.status_code,
            ", model id likely retired" if model_not_found else "",
            exc.response.text[:300],
        )
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openrouter", model_id=s.openrouter_embed_model,
            status_code=exc.response.status_code, model_not_found=model_not_found,
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("OpenRouter embedding request errored (model=%s): %s",
                     s.openrouter_embed_model, exc)
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openrouter", model_id=s.openrouter_embed_model,
        ) from exc
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
        # 20s, not 30s — see _openrouter_client()'s comment above. This
        # client is also called synchronously in a user-facing request
        # (ingest_course, per chunk), same 30s platform ceiling applies.
        timeout=20.0,
    )


def _openai_embed(text: str, *, input_type: str) -> list[float]:
    s = get_settings()
    try:
        with _openai_client() as c:
            r = c.post("/embeddings", json={
                "model": s.openai_embed_model,
                "input": text,
                "dimensions": 1024,  # matches vector(1024); OpenAI truncates+renormalizes server-side
            })
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "OpenAI embedding request failed (model=%s, status=%s): %s",
            s.openai_embed_model, exc.response.status_code, exc.response.text[:300],
        )
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openai", model_id=s.openai_embed_model,
            status_code=exc.response.status_code,
            model_not_found=exc.response.status_code == 404,
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("OpenAI embedding request errored (model=%s): %s",
                     s.openai_embed_model, exc)
        raise ModelUnavailableError(
            "Kala's model provider is unavailable right now. Please try again.",
            provider="openai", model_id=s.openai_embed_model,
        ) from exc
    return data["data"][0]["embedding"]
