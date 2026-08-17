"""De-identify before every model call. Send pseudonyms and stripped context,
never student names or raw PII. This is a hard rule from the root CLAUDE.md."""
from __future__ import annotations

import re

from app.deps import CurrentUser


def safe_context(user: CurrentUser, text: str) -> str:
    """Return context safe to send to a model: no names, no emails."""
    cleaned = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text or "")
    return f"[subject: {user.user_id[:8]}] {cleaned}".strip()
