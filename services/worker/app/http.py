"""HTTP entrypoint for the worker as a Vercel service.

The worker's real trigger is EventBridge at deploy time (see
infra/terraform/eventbridge.tf). On Vercel, scheduled jobs route through the
public rewrite table (vercel.json sends /api/worker to this service), so
expose a minimal ASGI app that runs the same handler() and returns its result
as JSON. No framework dependency: a bare ASGI callable is all the Python
runtime needs, and it keeps this package free of FastAPI.
"""
from __future__ import annotations

import json

from app.handler import handler


async def app(scope, receive, send) -> None:
    if scope["type"] != "http":
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"not found"})
        return

    method = scope.get("method", "GET")
    path = scope.get("path", "")
    if method not in ("GET", "POST") or not path.startswith("/api/worker"):
        await _respond(send, 404, {"error": "not found"})
        return

    # TODO: decode the cron/EventBridge event once the worker implements real
    # jobs (twin recompute + re-embed). The handler is idempotent and safe to
    # retry, so a scheduled ping today just reports the stub result.
    result = handler({}, None)
    await _respond(send, 200, result)


async def _respond(send, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
