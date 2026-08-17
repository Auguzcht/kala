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
    bedrock_model_tier1: str = Field(default="", alias="BEDROCK_MODEL_TIER1")
    bedrock_model_tier2: str = Field(default="", alias="BEDROCK_MODEL_TIER2")
    bedrock_embed_model: str = Field(default="", alias="BEDROCK_EMBED_MODEL")

    # LTI 1.3
    lti_issuer: str = Field(default="https://blackboard.com", alias="LTI_ISSUER")
    lti_client_id: str = Field(default="", alias="LTI_CLIENT_ID")
    lti_auth_login_url: str = Field(default="", alias="LTI_AUTH_LOGIN_URL")
    lti_auth_token_url: str = Field(default="", alias="LTI_AUTH_TOKEN_URL")
    lti_keyset_url: str = Field(default="", alias="LTI_KEYSET_URL")
    lti_deployment_ids: str = Field(default="", alias="LTI_DEPLOYMENT_IDS")
    lti_tool_private_key_pem: str = Field(default="", alias="LTI_TOOL_PRIVATE_KEY_PEM")

    @property
    def deployment_id_list(self) -> list[str]:
        return [d.strip() for d in self.lti_deployment_ids.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    _load_secrets_into_env()
    return Settings()
