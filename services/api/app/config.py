"""Application settings. Values come from environment variables, or from AWS
Secrets Manager when KALA_SECRETS_ARN is set (so infra can inject secrets
without putting them in env). Never log these values."""
from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_secrets_into_env() -> None:
    """If KALA_SECRETS_ARN is set, pull the JSON secret and place any missing
    keys into the environment before Settings is constructed."""
    arn = os.getenv("KALA_SECRETS_ARN")
    if not arn:
        return
    try:
        import boto3  # imported lazily so local dev without boto3 still works

        client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION"))
        raw = client.get_secret_value(SecretId=arn)["SecretString"]
        for key, value in json.loads(raw).items():
            os.environ.setdefault(key, str(value))
    except Exception as exc:  # never crash on secrets loading; surface in logs
        print(f"warning: could not load secrets from {arn}: {exc}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_key: str = Field(default="", alias="SUPABASE_SERVICE_KEY")
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")

    # Frontend / session
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    session_ttl_seconds: int = Field(default=3600, alias="SESSION_TTL_SECONDS")

    # AWS / Bedrock
    aws_region: str = Field(default="ap-southeast-1", alias="AWS_REGION")
    bedrock_model_fast: str = Field(default="", alias="BEDROCK_MODEL_FAST")
    bedrock_model_default: str = Field(default="", alias="BEDROCK_MODEL_DEFAULT")
    bedrock_model_reasoning: str = Field(default="", alias="BEDROCK_MODEL_REASONING")
    # Parity with openrouter_model_chat. This environment runs AI_PROVIDER=openrouter
    # so it is unused today, but every other role is mirrored across both
    # providers and an unmirrored one would be a silent trap the day Bedrock
    # access lands (get_model_for would KeyError on "chat").
    bedrock_model_chat: str = Field(default="", alias="BEDROCK_MODEL_CHAT")
    bedrock_model_premium: str = Field(default="", alias="BEDROCK_MODEL_PREMIUM")
    bedrock_embed_model: str = Field(default="", alias="BEDROCK_EMBED_MODEL")

    # Model provider switch. "bedrock" (default, for when this runs under the
    # school's AWS org account with real model access) or "openrouter" (the
    # interim path while Bedrock model access isn't provisioned yet, using
    # OpenRouter's free-tier models). ai/bedrock.py dispatches on this; every
    # caller (ai/router.py, ai/rag.py, ai/skill_proposer.py, learn/items.py,
    # routers/diagnostic.py) is unchanged either way, same converse()/embed()
    # signatures regardless of which provider is actually behind them.
    ai_provider: str = Field(default="bedrock", alias="AI_PROVIDER")

    # OpenRouter (interim provider). Free-tier chat models rotate and get
    # RETIRED without notice — see https://openrouter.ai/collections/free-models.
    # A retired id does not 400/401, it 404s (unknown model), which used to
    # surface as a raw 500 from every model-backed endpoint until
    # ai/bedrock.py learned to translate it (see _openrouter_converse).
    #
    # The defaults favour InclusionAI's general-purpose Flash model for
    # conversational turns. Nex AGI remains out of the primary rotation: it
    # was listed but served repeated 503s/read timeouts in production on
    # 2026-09-15.
    #
    # ITEM + DEFAULT + FALLBACK are deepseek/deepseek-v4.1-flash:floor
    # (2026-09-16). This is the model that survived live testing where every
    # free-tier candidate did not: liquid/lfm-2.5-2.6b:free answered once then
    # 429'd on even a 10-token call (account-level rate limit, exhausted),
    # inclusionai/* 404'd on any structured request, cohere/north-mini-code
    # accepted response_format but returned its own JSON shape, and the
    # previous fallback slug (deepseek/deepseek-v4.1-flash:free) was RETIRED by
    # OpenRouter. deepseek-v4.1-flash:floor measured 5/5 then 10/10 on the real
    # MCQ request under concurrency. The `:floor` suffix routes to whichever
    # provider serves this exact model cheapest — same model, no behaviour
    # change, just a cheaper provider pick.
    #
    # Cheaper sibling tested 2026-09-16 and REJECTED (recorded so it is not
    # re-litigated): ~deepseek/deepseek-v4-flash-latest ($0.04/$0.10 per M vs
    # this model's $0.15/$0.60) passed a single call schema-clean but dropped
    # 1 item in 25 real concurrent MCQ requests (truncated JSON,
    # finish_reason=length) and intermittently 400'd under load. Partial
    # tolerance (ai/concurrency.map_concurrent_partial) means a drop only
    # shortens a set rather than failing it, so it is not harmful — but at
    # fractions of a cent per set the saving is not worth a ~4% item-drop rate.
    # Revisit only if generation volume ever makes the delta material.
    #
    # Deliberately NOT the NVIDIA nemotron free models despite their headline
    # speed: both leak their full chain of thought into the message content
    # ("Here's a thinking process: …"), which reaches the student, and burns
    # the response budget on the monologue so the real answer never arrives.
    # ai/reasoning.py strips a leaked preamble defensively, but the right fix
    # is not to pick a model that needs stripping in the first place.
    #
    # All stay env-overridable (OPENROUTER_MODEL_*) so swapping the interim
    # provider for Bedrock later is a config change, never a code one.
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL",
    )
    openrouter_model_fast: str = Field(
        # fast/tag is the ONLY role tag_content uses, and it is called once per
        # chunk during ingest — the highest-volume model call in the system.
        # It pointed at a free model whose daily allowance is routinely
        # exhausted, which made tagging silently return null for every chunk
        # (verified live: the model 429'd "free-models-per-day" while the same
        # request on deepseek-v4.1-flash:floor returned the correct skill_id).
        # Untagged content never surfaces for a skill, so the failure looked
        # like "no content" rather than "tagger was down". Same working model
        # as item/default/fallback.
        default="deepseek/deepseek-v4.1-flash:floor", alias="OPENROUTER_MODEL_FAST",
    )
    openrouter_model_default: str = Field(
        default="deepseek/deepseek-v4.1-flash:floor", alias="OPENROUTER_MODEL_DEFAULT",
    )
    # The tutor's own role, deliberately SEPARATE from `default`.
    #
    # `default` is not tutor-only: learn/lessons.py phase 2, ai/skill_proposer.py,
    # and ai/prescriber.py's recommend() all call it. Repointing `default` would
    # have moved all four onto an unbenchmarked model at once. This role is
    # wired ONLY into routers/tutor.py's two answer() calls, so everything else
    # keeps exactly the behaviour it already had.
    #
    # WHY THE TUTOR NEEDED ITS OWN MODEL AT ALL: deepseek takes 34-103s on the
    # real tutor prompt (measured), and the request runs inside a 30s Lambda
    # wall behind a 25s client timeout, so every answer timed out and fell back
    # to another deepseek call that also could not fit. Result: an unhandled
    # 500 on every message.
    #
    # PAID slug, not the :free variant. Verified 2026-09-24: the free slug now
    # returns HTTP 404 "This model is unavailable for free. The paid version is
    # available now". The earlier benchmark measured the free one; it is gone.
    # Paid measures 4.8-6.4s here, faster and more consistent than the free
    # tier it replaces.
    openrouter_model_chat: str = Field(
        default="inclusionai/ling-3.0-flash-vl", alias="OPENROUTER_MODEL_CHAT",
    )
    # Fallback for the chat role specifically.
    #
    # The global openrouter_model_fallback is deepseek, which CANNOT serve as
    # the tutor's fallback: it takes 34-103s, so a failed primary would fall
    # back to another call that blows the same 25s timeout. The 500 would just
    # relocate rather than go away.
    #
    # nex-agi/nex-n2.5-mini was benchmarked on the REAL tutor prompt before
    # being wired in (not a toy prompt): 1.8-2.5s across four runs, no empty
    # responses, and a read-through of a full answer showed accurate, grounded,
    # well-structured teaching. Deliberately a DIFFERENT provider from the
    # primary, so a ling/InclusionAI-specific outage does not take out both.
    openrouter_model_chat_fallback: str = Field(
        default="nex-agi/nex-n2.5-mini:free",
        alias="OPENROUTER_MODEL_CHAT_FALLBACK",
    )
    openrouter_model_reasoning: str = Field(
        default="inclusionai/ling-3.0-flash-vl", alias="OPENROUTER_MODEL_REASONING",
    )
    # Reasoning runs inline for lesson outlines and skill proposals, so its
    # fallback must also fit the API Lambda wall. DeepSeek can take 34-103s
    # on these calls and is not suitable as the inline fallback.
    openrouter_model_reasoning_fallback: str = Field(
        default="nex-agi/nex-n2.5-mini:free",
        alias="OPENROUTER_MODEL_REASONING_FALLBACK",
    )
    openrouter_model_premium: str = Field(
        default="inclusionai/ling-3.0-flash-vl", alias="OPENROUTER_MODEL_PREMIUM",
    )
    openrouter_model_item: str = Field(
        default="deepseek/deepseek-v4.1-flash:floor",
        alias="OPENROUTER_MODEL_ITEM",
    )
    # Same model as the primary. Kept as its own knob so a future primary can
    # still name an explicit different-provider escape hatch; today both point
    # at the one model that measurably works.
    openrouter_model_fallback: str = Field(
        default="deepseek/deepseek-v4.1-flash:floor",
        alias="OPENROUTER_MODEL_FALLBACK",
    )
    # Comma-separated provider preference for OpenRouter's routing (its
    # `provider.order` field). Empty = no preference, i.e. whatever OpenRouter
    # picks, which is the pre-existing behavior.
    #
    # WHY THIS EXISTS: one model id is served by FIFTEEN providers here and
    # OpenRouter load-balances across all of them. Measured 2026-09-21, same
    # prompt and budget: unpinned 32/64/113s, pinned to Relace 2.8-8.5s. That
    # spread is what pushed tutor requests past the 30s Lambda wall.
    #
    # Sent as `order` with allow_fallbacks LEFT TRUE (see ai/bedrock.py) — a
    # hard pin would 503 whenever the preferred provider is at capacity,
    # trading a slow success for a fast failure. This is a preference, not a
    # requirement. Swappable without a code change as the provider mix shifts.
    openrouter_provider_order: str = Field(
        default="Relace", alias="OPENROUTER_PROVIDER_ORDER",
    )
    # Nemotron 3 Embed 1B natively outputs 2048 dims; ai/bedrock.py slices to
    # the first 1024 and re-normalizes (NVIDIA's own documented technique for
    # this model family) so it matches the existing vector(1024) schema with
    # no migration change. Note: this id is ALSO no longer served on
    # OpenRouter at the time of writing, so the OpenRouter embed path is
    # effectively unavailable — which is exactly why EMBED_PROVIDER defaults
    # to "openai" below and production runs embeddings there. Left in place
    # as the documented Bedrock-parity fallback; embeddings never depend on
    # the chat provider.
    openrouter_embed_model: str = Field(
        default="nvidia/nemotron-3-embed-1b:free", alias="OPENROUTER_EMBED_MODEL",
    )

    # Embeddings can use a different provider than chat completions. Live
    # testing found OpenRouter's free NVIDIA embedding endpoint consistently
    # 500ing (unrelated to the input_type bug already fixed, the endpoint
    # itself is unhealthy), while its free chat models work fine. Empty
    # string (default) means "use AI_PROVIDER for embeddings too", set
    # explicitly to "openai" to embed via OpenAI instead while chat stays on
    # OpenRouter. Independent of AI_PROVIDER on purpose, chat and embedding
    # reliability are two separate problems.
    embed_provider: str = Field(default="", alias="EMBED_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    # text-embedding-3-small officially supports a "dimensions" request
    # parameter (OpenAI truncates + renormalizes server-side, the same
    # Matryoshka technique used manually for the NVIDIA path, but here it's
    # a first-class supported feature) -- so this matches vector(1024) with
    # no manual slicing needed. $0.02 / 1M tokens: embedding an entire
    # course's content costs cents, not dollars.
    openai_embed_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL")

    # LTI 1.3
    lti_issuer: str = Field(default="https://blackboard.com", alias="LTI_ISSUER")
    lti_client_id: str = Field(default="", alias="LTI_CLIENT_ID")
    lms_verify_tls: bool = Field(default=True, alias="LMS_VERIFY_TLS")
    lti_auth_login_url: str = Field(default="", alias="LTI_AUTH_LOGIN_URL")
    lti_auth_token_url: str = Field(default="", alias="LTI_AUTH_TOKEN_URL")
    lti_keyset_url: str = Field(default="", alias="LTI_KEYSET_URL")
    lti_deployment_ids: str = Field(default="", alias="LTI_DEPLOYMENT_IDS")
    lti_tool_private_key_pem: str = Field(default="", alias="LTI_TOOL_PRIVATE_KEY_PEM")

    # Blackboard Learn REST API
    lms_rest_base_url: str = Field(default="", alias="LMS_REST_BASE_URL")
    lms_rest_client_id: str = Field(default="", alias="LMS_REST_CLIENT_ID")
    lms_rest_client_secret: str = Field(default="", alias="LMS_REST_CLIENT_SECRET")

    @property
    def deployment_id_list(self) -> list[str]:
        return [d.strip() for d in self.lti_deployment_ids.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    _load_secrets_into_env()
    return Settings()
