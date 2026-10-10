"""Shared classification for HTTP errors returned by model providers."""
from __future__ import annotations

import json

PERMANENT_MODEL_STATUSES = {400, 401, 403, 404, 422}


class ModelCallError(RuntimeError):
    def __init__(self, status_code: int, reason: str):
        self.status_code = int(status_code)
        self.reason = reason[:500]
        self.permanent = self.status_code in PERMANENT_MODEL_STATUSES
        self.throttled = self.status_code == 429
        self.transient = self.throttled or self.status_code >= 500
        super().__init__(f"model HTTP {self.status_code}: {self.reason}")


def error_reason(response, protected: tuple[str, ...] = ()) -> str:
    """Return a short provider error detail, scrubbing request text first."""
    try:
        data = response.json()
        detail = data.get("error", data) if isinstance(data, dict) else data
        if isinstance(detail, dict):
            detail = {key: detail.get(key) for key in ("message", "code", "type") if detail.get(key) is not None}
        body = json.dumps(detail, ensure_ascii=False)
    except (TypeError, ValueError):
        body = response.text
    for value in protected:
        if value:
            body = body.replace(value, "[redacted]")
    return body[:500]
