"""Supabase Storage access with the service-role key, for the tutor's
private study-aid uploads (migration 0011). Separate module from
db/supabase.py because Storage is a different REST API (storage/v1, not
rest/v1) with binary bodies, not JSON — sharing one _client() helper
between them would mean every JSON call carrying storage's binary
concerns or vice versa. Same trust model as db/supabase.py: the service
role bypasses bucket RLS, so this is the trusted write path, and nothing
here is reachable from the browser directly.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

BUCKET = "tutor-attachments"


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=f"{s.supabase_url}/storage/v1",
        headers={
            "apikey": s.supabase_service_key,
            "Authorization": f"Bearer {s.supabase_service_key}",
        },
        timeout=30.0,
    )


def upload(path: str, content: bytes, mime_type: str) -> None:
    with _client() as c:
        r = c.post(
            f"/object/{BUCKET}/{path}",
            content=content,
            headers={"Content-Type": mime_type},
        )
        r.raise_for_status()


def delete(path: str) -> None:
    with _client() as c:
        r = c.delete(f"/object/{BUCKET}/{path}")
        # A file that's already gone shouldn't block deleting the metadata
        # row that points at it — 404 is fine here, anything else isn't.
        if r.status_code not in (200, 404):
            r.raise_for_status()
