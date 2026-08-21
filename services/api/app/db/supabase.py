"""Supabase access with the service-role key. The service role bypasses RLS,
so this module is the trusted write path (evidence, upserts, twin state).
Uses the PostgREST HTTP API via httpx. For heavier tracer math you may prefer
a direct psycopg connection; the interface here stays small on purpose."""
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
        timeout=15.0,
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


def rpc(fn: str, args: dict[str, Any]) -> Any:
    with _client() as c:
        r = c.post(f"/rpc/{fn}", json=args)
        r.raise_for_status()
        return r.json() if r.content else None


# ---- domain helpers -------------------------------------------------------

def get_or_create_institution(*, iss: str, deployment_id: str, name: str, lms_type: str) -> dict:
    found = select("institutions", {
        "lms_issuer": f"eq.{iss}",
        "deployment_id": f"eq.{deployment_id}",
        "select": "*",
        "limit": "1",
    })
    if found:
        return found[0]
    created = insert("institutions", [{
        "name": name, "lms_type": lms_type,
        "lms_issuer": iss, "deployment_id": deployment_id,
    }])
    return created[0]


def upsert_user(*, institution_id: str, lms_user_id: str, role: str,
                display_name: str | None, email: str | None) -> dict:
    rows = upsert("users", [{
        "institution_id": institution_id,
        "lms_user_id": lms_user_id,
        "role": role,
        "pseudonym": f"anon-{lms_user_id[:12]}",
    }], on_conflict="institution_id,lms_user_id")
    user = rows[0]
    if display_name or email:
        upsert("user_profiles", [{
            "user_id": user["id"],
            "display_name": display_name,
            "email": email,
        }], on_conflict="user_id")
    return user


def get_or_create_course(*, institution_id: str, lms_course_id: str, title: str) -> dict:
    rows = upsert("courses", [{
        "institution_id": institution_id,
        "lms_course_id": lms_course_id,
        "title": title,
    }], on_conflict="institution_id,lms_course_id")
    return rows[0]


def upsert_enrollment(*, institution_id: str, user_id: str, course_id: str, role: str) -> None:
    upsert("enrollments", [{
        "institution_id": institution_id,
        "user_id": user_id,
        "course_id": course_id,
        "role": "instructor" if role in ("instructor", "admin") else "student",
    }], on_conflict="user_id,course_id")


def insert_evidence(rows: list[dict]) -> list[dict]:
    return insert("evidence_events", rows, prefer="return=representation")
