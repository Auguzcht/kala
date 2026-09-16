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
import time

import httpx

from app.ai.errors import ModelUnavailableError
from app.config import get_settings

logger = logging.getLogger(__name__)

# How long to wait before retrying a rate-limited/overloaded primary on the
# fallback model. See converse().
_FALLBACK_BACKOFF_SECONDS = 1.5

# ---------------------------------------------------------------------------
# READ THIS BEFORE PASSING max_tokens.
#
# Reasoning models (the DeepSeek v4.1 family we route to, and most current
# frontier models) THINK BEFORE THEY ANSWER, and the thinking is billed against
# max_tokens exactly like the answer is. If the budget runs out mid-thought, the
# call returns finish_reason="length" with EMPTY content -- the answer was never
# written. That is an absence, not an error, so it does not raise: it lands in
# the caller as a parse failure or a null, and gets misread as "the model found
# nothing" rather than "the model never got to reply".
#
# This has already cost three debugging rounds in this codebase:
#   generate_question  768  -> 1536   (truncated MCQs)
#   tag_content        256  -> 2048   (EVERY tag came back null)
#   tag_content       2048  -> 4096   (still failed, but only on LONG inputs,
#                                      so it looked fixed while silently
#                                      failing on the most valuable content)
#
# The rule, stated generally so the next call site does not repeat it:
#
#   SIZE FOR THE LONGEST REALISTIC INPUT, NOT THE TYPICAL ONE.
#   Reasoning length scales with input length and task difficulty.
#   A budget that passes your test fixture can still truncate in production,
#   because your fixture is short and easy. Measure the worst case (a long
#   document, a hard extraction) and size for that.
#
# Practical guidance: treat ~1024 as the absolute floor for anything with real
# input, and reach for 4096 when the input can be a whole document (tagging,
# extraction, question generation from a long chunk). A too-small budget does
# NOT fail loudly, so it will not be caught by happy-path testing.
#
# When adding a caller: measure, do not estimate. Send the longest realistic
# input and check finish_reason is "stop", not "length".
# ---------------------------------------------------------------------------
_MAX_TOKENS_FLOOR = 1024


def converse(
    *,
    model_id: str,
    system: str,
    messages: list[dict],
    # Raised from 1024 to the documented floor. A caller that omits max_tokens
    # should not silently inherit a budget that reasoning will eat -- but note
    # this is still only a FLOOR: document-sized inputs need 4096. See above.
    max_tokens: int = _MAX_TOKENS_FLOOR,
    response_format: dict | None = None,
) -> str:
    s = get_settings()
    # A budget this small cannot survive a reasoning preamble, so the call will
    # return empty content and the caller will misread it as a model that found
    # nothing. Warn once per call site instead of failing, since a deliberately
    # tiny budget is legal for a one-word classification task.
    if max_tokens < _MAX_TOKENS_FLOOR:
        logger.warning(
            "converse called with max_tokens=%d < %d floor (model=%s). If this "
            "model reasons, the response may be truncated to empty and read as "
            "a null result rather than an error. See the max_tokens note above.",
            max_tokens, _MAX_TOKENS_FLOOR, model_id,
        )
    if s.ai_provider == "openrouter":
        request = {
            "model_id": model_id,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            request["response_format"] = response_format
        try:
            return _openrouter_converse(**request)
        except ModelUnavailableError as exc:
            # A model being present in OpenRouter's catalogue does not mean
            # its provider has capacity. Give transient provider failures one
            # chance on a separate provider before exposing the outage to the
            # student. Do not retry bad credentials or malformed requests.
            fallback = getattr(s, "openrouter_model_fallback", "")
            if not fallback or fallback == model_id or not _can_fallback(exc):
                raise
            # Back off before retrying a rate limit or a transient 5xx. An
            # immediate retry is what turns one 429 into two, and the whole
            # point of the fallback is to reach a DIFFERENT model that has
            # capacity -- hammering the same instant defeats that. Short and
            # bounded (the Lambda runs on a 30s wall; the client already has
            # an 8s timeout), so it never eats the request budget.
            if exc.status_code in {429, 503}:
                time.sleep(_FALLBACK_BACKOFF_SECONDS)
            logger.warning(
                "OpenRouter primary unavailable (model=%s, status=%s); retrying with fallback model=%s",
                model_id, exc.status_code, fallback,
            )
            request["model_id"] = fallback
            return _openrouter_converse(**request)
    return _bedrock_converse(model_id=model_id, system=system, messages=messages, max_tokens=max_tokens)


def _can_fallback(exc: ModelUnavailableError) -> bool:
    """Only retry provider capacity/transport failures, never bad client config.

    ``None`` is an httpx transport error (including a read timeout). A 404 is
    included because free model IDs can disappear without warning. 400/401/403
    are deterministic request/key failures and a second model cannot fix them.
    """
    return exc.status_code is None or exc.status_code in {404, 408, 429, 500, 502, 503, 504}


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
        # 8s, not 20s: this client is called synchronously inside
        # user-facing requests (/lti/launch's skill proposal, /skills/propose,
        # tutor, item generation) that run on a 30s Lambda timeout behind an
        # API Gateway HTTP API integration — which hard-caps the wait at 30s
        # regardless of this client's own setting. A 60s timeout here meant
        # a hung free-tier model never raised its own httpx.TimeoutException;
        # the platform killed the whole Lambda first, with no exception for
        # the surrounding try/except (_seed_course_skills) to catch — silent
        # "Service Unavailable" instead of the clean "skipped" behavior that
        # code already has. Eight seconds leaves headroom for DB work and the
        # single cross-provider fallback attempt in converse() when a free
        # provider stalls.
        timeout=8.0,
    )


def _flatten_text(content) -> str:
    """Every current caller sends messages=[{"role": "user", "content":
    [{"text": "..."}]}] (the Bedrock Converse shape). Extract the text
    regardless of how many parts there are, so this doesn't silently drop
    content if that ever changes."""
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content)


def _openrouter_converse(
    *,
    model_id: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
    response_format: dict | None = None,
) -> str:
    oai_messages = [{"role": "system", "content": system}]
    for m in messages:
        oai_messages.append({"role": m["role"], "content": _flatten_text(m["content"])})

    try:
        data = _openrouter_post(
            model_id=model_id, messages=oai_messages,
            max_tokens=max_tokens, response_format=response_format,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        # Structured-output capability gap, not an outage. Our system prompts
        # already say "return strict JSON and nothing else", so response_format
        # is an ENHANCEMENT — a hard constraint only when the model's providers
        # advertise support. Free-tier churn means a model that supported
        # json_schema last week may 404 ``{"No endpoints found that can handle
        # the requested parameters"}`` today (response_format + the
        # require_parameters routing filter). Degrade to prompt-enforced JSON
        # once and carry on, rather than failing the whole request: this is
        # what keeps item generation alive across model churn without needing
        # someone to re-curate OPENROUTER_MODEL_* every time a provider drops
        # structured output.
        if (
            response_format is not None
            and status_code == 404
            and _is_provider_parameter_rejection(exc.response.text)
        ):
            logger.warning(
                "OpenRouter model %s cannot route a structured request; "
                "retrying without response_format and relying on the prompt's "
                "JSON instruction.", model_id,
            )
            try:
                data = _openrouter_post(
                    model_id=model_id, messages=oai_messages,
                    max_tokens=max_tokens, response_format=None,
                )
            except httpx.HTTPStatusError as retry_exc:
                exc = retry_exc
                status_code = retry_exc.response.status_code
            except httpx.HTTPError as retry_exc:
                logger.error("OpenRouter request errored (model=%s): %s", model_id, retry_exc)
                raise ModelUnavailableError(
                    "Kala's model provider is unavailable right now. Please try again.",
                    provider="openrouter", model_id=model_id,
                ) from retry_exc
            else:
                return _openrouter_content(data)
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
    return _openrouter_content(data)


def _is_provider_parameter_rejection(body: str) -> bool:
    """True when OpenRouter's 404 is specifically its routing filter rejecting
    the request's parameters (e.g. response_format unsupported by every
    endpoint for that model), NOT an unknown model id.

    Both are 404s, so they must be told apart: an unknown model is fatal (a
    retry can't help and the id needs changing), while a parameter rejection
    is recoverable by dropping the parameter and relying on the prompt. The
    distinguishing text is OpenRouter's own routing-funnel message.
    """
    text = body.lower()
    return "no endpoints found" in text and (
        "requested parameters" in text or "provider routing" in text
    )


def _openrouter_post(
    *,
    model_id: str,
    messages: list[dict],
    max_tokens: int,
    response_format: dict | None,
) -> dict:
    """One OpenRouter chat completion. Raises httpx.HTTPStatusError on a
    non-2xx so the caller can classify it (structured-output rejection vs
    unknown model vs outage).

    Deliberately does NOT send provider.require_parameters — see the comment
    at the call site for why (it blocks capable models).
    """
    payload: dict = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    if response_format is not None:
        # response_format WITHOUT provider.require_parameters.
        #
        # require_parameters guarantees we never land on a provider that
        # ignores the schema -- but it also hard-404s any model whose endpoints
        # don't advertise the parameter, even when that model CAN answer. Live
        # test: cohere/north-mini-code:free 404s with require_parameters, and
        # answers fine without it; inclusionai/* 404s the same way. So the
        # filter was rejecting capable models to defend against a failure we
        # already catch downstream: a model that ignores the schema returns
        # JSON that _validated_mcq rejects, which now retries (items.py) and
        # ultimately surfaces a clean error. Prefer "try it and validate" over
        # "refuse to try".
        payload["response_format"] = response_format
    with _openrouter_client() as c:
        r = c.post("/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()


def _openrouter_content(data: dict) -> str:
    """Extract the assistant text from a chat-completion response, tolerating
    the two shapes that otherwise blow up as opaque parse errors downstream:
    a message whose content is null (some models emit only a reasoning field),
    and an empty choices array. Returns '' in those cases — callers already
    treat empty content as an invalid item and surface a clean retry message,
    which is far better than a KeyError/JSONDecodeError with no explanation.
    """
    choices = data.get("choices") or []
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content") or ""


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
