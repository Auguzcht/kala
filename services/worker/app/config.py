"""Worker settings. Deliberately a slim duplicate of services/api/app/config.py,
not a shared import — see app/handler.py's module docstring for why. Only the
fields the worker's jobs actually touch are kept here: Supabase access, the
embedding provider path (embed backfill needs the same provider switch the api
uses), and the tag model (tag backfill classifies chunks against the same
OpenRouter model the api's tagger uses).

If a setting here drifts from the api's copy, that is a real risk (e.g. an
embedding model change made in one place and not the other). Grep both files
for the field name before changing either one.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_secrets_into_env() -> None:
    arn = os.getenv("KALA_SECRETS_ARN")
    if not arn:
        return
    try:
        import boto3

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

    # AWS / Bedrock
    aws_region: str = Field(default="ap-southeast-1", alias="AWS_REGION")
    bedrock_embed_model: str = Field(default="", alias="BEDROCK_EMBED_MODEL")

    # Same provider switch as services/api (see that config.py for the full
    # rationale). The worker calls embed() for the backfill job and the tag
    # model for the tag-backfill job; it never calls converse() for anything
    # else.
    ai_provider: str = Field(default="bedrock", alias="AI_PROVIDER")
    embed_provider: str = Field(default="", alias="EMBED_PROVIDER")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL",
    )
    openrouter_embed_model: str = Field(
        default="nvidia/nemotron-3-embed-1b:free", alias="OPENROUTER_EMBED_MODEL",
    )

    # The tag model. MUST match services/api/app/config.py's openrouter_model_fast
    # (the api maps both the "fast" and "tag" roles to that one key). The tag
    # backfill job classifies chunks against this model, so a change on the api
    # side that is not mirrored here would tag with a different (possibly
    # free-tier, rate-limited) model than the request path uses. The default
    # here is the paid, structured-output-reliable model the api settled on
    # after a free model's daily allowance kept returning empty tags. Kept
    # env-overridable (OPENROUTER_MODEL_FAST) so a provider swap stays a config
    # change, never a code one — same contract as the api.
    openrouter_model_fast: str = Field(
        default="deepseek/deepseek-v4.1-flash:floor", alias="OPENROUTER_MODEL_FAST",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_embed_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL")

    # Twin tracer step size. MUST match services/api/app/twin/tracer.py's _K
    # exactly, or reconciliation replays evidence into a different estimate
    # than the live request path produced. Kept as a setting (not hardcoded)
    # so it is at least visible in one place if it needs tuning, but the
    # source of truth for the value is tracer.py; change both together.
    tracer_k: float = Field(default=0.15, alias="TRACER_K")


@lru_cache
def get_settings() -> Settings:
    _load_secrets_into_env()
    return Settings()
