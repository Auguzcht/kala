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

    # OpenRouter (interim provider). Free-tier chat models rotate over time,
    # see https://openrouter.ai/collections/free-models, current defaults
    # below were verified working as of this integration.
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL",
    )
    openrouter_model_fast: str = Field(
        default="nvidia/nemotron-3.5-lightning:free", alias="OPENROUTER_MODEL_FAST",
    )
    openrouter_model_default: str = Field(
        default="z-ai/glm-5.2:free", alias="OPENROUTER_MODEL_DEFAULT",
    )
    openrouter_model_reasoning: str = Field(
        default="z-ai/glm-5.2:free", alias="OPENROUTER_MODEL_REASONING",
    )
    openrouter_model_premium: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free", alias="OPENROUTER_MODEL_PREMIUM",
    )
    # Nemotron 3 Embed 1B natively outputs 2048 dims; ai/bedrock.py slices to
    # the first 1024 and re-normalizes (NVIDIA's own documented technique for
    # this model family) so it matches the existing vector(1024) schema with
    # no migration change.
    openrouter_embed_model: str = Field(
        default="nvidia/nemotron-3-embed-1b:free", alias="OPENROUTER_EMBED_MODEL",
    )

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
