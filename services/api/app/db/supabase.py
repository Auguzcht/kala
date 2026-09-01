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
        timeout=60.0,  # vector rows (1024-dim embeddings) need headroom on slow/cold writes; 15s was pre-vector
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


def delete(table: str, filters: dict[str, str]) -> list[dict]:
    """Hard delete matching rows. There is no soft-delete convention in this
    schema outside evidence_events (which is append-only by trigger and must
    never be deleted); this exists for cleaning up regenerable derived rows
    like a failed/partial guided lesson's steps, never for user data."""
    with _client() as c:
        r = c.delete(f"/{table}", params=filters, headers={"Prefer": "return=representation"})
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


def remove_stale_student_enrollments(
    *, institution_id: str, course_id: str, keep_user_ids: list[str],
) -> list[dict]:
    """The other half of roster sync: NRPS pulls add members (upsert_enrollment,
    called per-member on every instructor launch); this removes STUDENT
    enrollments for the course whose user was NOT in that fresh pull.

    Without this, roster sync was additive-only forever, so a one-off dev
    launch or a student who dropped the course left a permanent phantom row
    with no path back to correct — exactly what turned into six "students"
    on the instructor dashboard when only two were real.

    Two things this deliberately does NOT do:

    - Touch instructor/admin enrollments. This is reconciling the LEARNER
      roster specifically. A co-teacher whose role mapping is ambiguous in
      one LMS response should never lose course access because of it. This
      is enforced by the `role = eq.student` filter below, not by trusting
      the caller to pass a complete keep-list — even if a launching
      instructor were somehow absent from a pull (they shouldn't be; a
      normal Blackboard roster listing includes them), their own
      role='instructor' row can never match this filter.
    - Touch users, user_profiles, or evidence_events. Removing someone's
      enrollment in THIS course says nothing about whether they still exist
      in other courses at this institution, and their evidence history is
      exactly the kind of thing that should survive a re-enrollment intact.

    Callers MUST NOT pass an empty keep_user_ids for "the class is empty" —
    see the guard in lti/routes.py._sync_roster, which never calls this
    unless the fresh pull actually returned at least one member. An empty
    list here would delete every real student enrollment in the course.
    """
    if not keep_user_ids:
        return []
    return delete("enrollments", {
        "institution_id": f"eq.{institution_id}",
        "course_id": f"eq.{course_id}",
        "role": "eq.student",
        "user_id": f"not.in.({','.join(keep_user_ids)})",
    })


def insert_evidence(rows: list[dict]) -> list[dict]:
    return insert("evidence_events", rows, prefer="return=representation")
