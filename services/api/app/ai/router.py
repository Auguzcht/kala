"""Tiered model router. Cheap default for most Q&A, hints, and RAG answers;
escalate for harder tasks. Keeps model choice in one place."""
from __future__ import annotations

from app.ai import bedrock
from app.config import get_settings


def answer(*, system: str, user_text: str, escalate: bool = False) -> str:
    s = get_settings()
    model = s.bedrock_model_tier2 if escalate else s.bedrock_model_tier1
    return bedrock.converse(
        model_id=model,
        system=system,
        messages=[{"role": "user", "content": [{"text": user_text}]}],
    )
