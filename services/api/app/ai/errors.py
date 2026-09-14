"""Errors raised by the model layer, kept separate from app/ai/bedrock.py so
callers (and the FastAPI exception handler in main.py) can import the type
without importing the provider implementation.

Why this exists: the model layer used to let httpx.HTTPStatusError escape
straight out of a request. When an OpenRouter model id is retired,
OpenRouter returns 404 (unknown model), raise_for_status() re-raises, and
every model-backed endpoint — tutor /ask, lesson generation, practice item
generation, misconception/explanation generation — returned a bare 500 with
no useful message. A provider-side outage or a stale model id is not a bug
in the request, so it should not read as one: it is a dependency being
unavailable, i.e. a 502/503. One shared type, one handler, so this is fixed
once at the layer every caller already goes through instead of patched
per-router.
"""
from __future__ import annotations


class ModelUnavailableError(RuntimeError):
    """The configured model provider could not serve the request: unknown/
    retired model id, provider 4xx, provider 5xx, timeout, or transport
    failure. Mapped to HTTP 502 by main.py's handler so the frontend shows a
    readable message instead of an opaque 500.

    `model_not_found` distinguishes the one case that is a configuration
    problem rather than a transient outage (see bedrock.py, which logs it
    distinctly) — it almost always means a free-tier model id was retired.
    """

    def __init__(self, message: str, *, provider: str, model_id: str,
                 status_code: int | None = None, model_not_found: bool = False):
        super().__init__(message)
        self.provider = provider
        self.model_id = model_id
        self.status_code = status_code
        self.model_not_found = model_not_found
