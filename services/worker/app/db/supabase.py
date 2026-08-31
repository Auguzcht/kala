"""Supabase access with the service-role key, for the worker.

Deliberate near-duplicate of services/api/app/db/supabase.py — the worker
Dockerfile only COPYs its own app/ directory (see the Dockerfile and
handler.py's docstring), so it cannot import services/api. Trimmed to the
generic select/insert/update/upsert/rpc primitives the worker's jobs use;
no domain helpers (get_or_create_course, etc.) since the worker never
creates institutions, users, or courses, only reads and updates existing
rows.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=f"{s.supabase_url}/rest/v1",
        headers={
            "apikey": s.supabase_service_key,
            "Authorization": f"Bearer {s.supabase_service_key}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    )


def select(table: str, params: dict[str, str]) -> list[dict]:
    with _client() as c:
        r = c.get(f"/{table}", params=params)
        r.raise_for_status()
        return r.json()


def insert(table: str, rows: list[dict], *, prefer: str = "return=representation") -> list[dict]:
    with _client() as c:
        r = c.post(f"/{table}", json=rows, headers={"Prefer": prefer})
        r.raise_for_status()
        return r.json() if r.content else []


def upsert(table: str, rows: list[dict], *, on_conflict: str) -> list[dict]:
    with _client() as c:
        r = c.post(
            f"/{table}",
            params={"on_conflict": on_conflict},
            json=rows,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        r.raise_for_status()
        return r.json() if r.content else []


def update(table: str, filters: dict[str, str], values: dict[str, Any]) -> list[dict]:
    with _client() as c:
        r = c.patch(f"/{table}", params=filters, json=values,
                    headers={"Prefer": "return=representation"})
        r.raise_for_status()
        return r.json() if r.content else []
