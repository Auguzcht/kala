"""De-identify before every model call. Send pseudonyms and stripped context,
never student names or raw PII. This is a hard rule from the root CLAUDE.md."""
from __future__ import annotations

import re

from app.deps import CurrentUser


def strip_pii(text: str) -> str:
    cleaned = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text or "")
    return re.sub(r"\b(?:姓名|name)\s*:\s*[^,;\n]+", "[name]", cleaned, flags=re.IGNORECASE)


def safe_context(user: CurrentUser, text: str) -> str:
    """Return context safe to send to a model: no names, no emails."""
    return f"[subject: {user.user_id[:8]}] {strip_pii(text)}".strip()
