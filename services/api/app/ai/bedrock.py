"""Thin Bedrock wrapper using the Converse API. Model ids come from settings;
confirm the exact ids available in your region before relying on them."""
from __future__ import annotations

import json

import boto3

from app.config import get_settings


def _runtime():
    s = get_settings()
    return boto3.client("bedrock-runtime", region_name=s.aws_region)


def converse(*, model_id: str, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
    resp = _runtime().converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    parts = resp["output"]["message"]["content"]
    return "".join(p.get("text", "") for p in parts)


def embed(text: str, *, input_type: str = "search_document") -> list[float]:
    s = get_settings()
    resp = _runtime().invoke_model(
        modelId=s.bedrock_embed_model,
        body=json.dumps({"texts": [text], "input_type": input_type}),
    )
    body = json.loads(resp["body"].read())
    return body["embeddings"][0]
