"""Worker settings. Deliberately a slim duplicate of services/api/app/config.py,
not a shared import — see app/handler.py's module docstring for why. Only the
fields the worker's jobs actually touch are kept here: Supabase access and the
embedding provider path (twin reconciliation and readiness need Supabase only;
the embedding backfill job needs the same provider switch the api uses).

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
    # rationale). The worker only ever calls embed(), never converse().
    ai_provider: str = Field(default="bedrock", alias="AI_PROVIDER")
    embed_provider: str = Field(default="", alias="EMBED_PROVIDER")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL",
    )
    openrouter_embed_model: str = Field(
        default="nvidia/nemotron-3-embed-1b:free", alias="OPENROUTER_EMBED_MODEL",
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
