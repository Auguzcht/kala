"""Supabase access with the service-role key. The service role bypasses RLS,
so this module is the trusted write path (evidence, upserts, twin state).
Uses the PostgREST HTTP API via httpx. For heavier tracer math you may prefer
a direct psycopg connection; the interface here stays small on purpose."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


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


def resolve_user(*, institution_id: str, lms_user_id: str, role: str,
                 display_name: str | None, email: str | None) -> dict:
    """Resolve an LMS identity to the ONE Kala user it belongs to, creating one
    only if genuinely new. This is the fix for duplicate accounts — see
    migration 0015 for the full WHY.

    Resolution order, and each step exists for a reason:

      1. ALIAS LOOKUP (exact, stable). `lms_identity_aliases` maps any LMS
         identifier Kala has seen to a user. This is the fast path once a
         person has launched once, and it does not care whether the identifier
         is an LTI `sub` or a REST `userId`.

      2. EMAIL MATCH (discovery). `users.lms_user_id` is written from `sub` on
         launch and from the connector's `userId` on roster sync — two
         different values for the same person. If the launch's email matches an
         existing profile, that IS the same human, so resolve to them instead of
         minting a twin. Both paths already fetch email; it matched exactly in
         every observed duplicate pair.

      3. CREATE. Nothing matched, so this really is a new person.

    NOTHING HERE IS OPTIONAL. Two hard requirements:

      - The `lms_user_id` fallback in step 3 STAYS. Email can be absent from an
        LTI launch and is not guaranteed unique; if resolution depended on it,
        a launch without an email would stop working entirely.
      - The alias is written on EVERY successful resolution (step 4), not just
        for new users. Recording the pair the first time it is OBSERVED is what
        lets step 1 take over later — and it also back-fills the other
        identifier for a user who was matched by email, so the NEXT launch hits
        the exact path.

    Matching on email is deliberately a discovery signal, never a permanent
    key: email is mutable, and an address change must not fork an account. The
    alias row is what makes the resolution durable.
    """
    # 1. Exact alias hit.
    aliases = select("lms_identity_aliases", {
        "institution_id": f"eq.{institution_id}",
        "lms_user_id": f"eq.{lms_user_id}",
        "select": "user_id", "limit": "1",
    })
    if aliases:
        user = _user_by_id(aliases[0]["user_id"])
        if user:
            _touch_profile(user_id=user["id"], display_name=display_name, email=email)
            record_identity_alias(
                institution_id=institution_id, lms_user_id=lms_user_id,
                user_id=user["id"], source="launch",
            )
            return user

    # 2. Email match against an existing profile (same institution).
    if email:
        matched = _user_by_email(institution_id=institution_id, email=email)
        if matched:
            # Adopt this launch's identifier as an alias for that user, so the
            # sub and the roster userId converge on ONE account from here on.
            record_identity_alias(
                institution_id=institution_id, lms_user_id=lms_user_id,
                user_id=matched["id"], source="email_match",
            )
            _touch_profile(user_id=matched["id"], display_name=display_name, email=email)
            return matched

    # 3. Genuinely new. The lms_user_id fallback stays: a launch with no email
    #    must still work.
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

    # 4. Record the alias on EVERY resolution, not just new users.
    record_identity_alias(
        institution_id=institution_id, lms_user_id=lms_user_id,
        user_id=user["id"], source="launch",
    )
    return user


def record_identity_alias(*, institution_id: str, lms_user_id: str,
                          user_id: str, source: str) -> None:
    """Map an LMS identifier to a user, idempotently.

    `on_conflict` + a no-op update means re-seeing the same pair is harmless,
    while the `source` is left as whatever FIRST learned the mapping — that
    value is diagnostic, and letting a later sighting overwrite it would lose
    which path originally discovered the identity.
    """
    upsert("lms_identity_aliases", [{
        "institution_id": institution_id,
        "lms_user_id": lms_user_id,
        "user_id": user_id,
        "source": source,
    }], on_conflict="institution_id,lms_user_id")


def resolve_user_by_email(*, institution_id: str, email: str) -> dict | None:
    """The single user whose profile carries this email in this institution, or
    None. Used by the roster sync and the repair script; the launch path goes
    through resolve_user()."""
    return _user_by_email(institution_id=institution_id, email=email)


def _user_by_id(user_id: str) -> dict | None:
    rows = select("users", {"id": f"eq.{user_id}", "select": "id,institution_id,lms_user_id,role", "limit": "1"})
    return rows[0] if rows else None


def _user_by_email(*, institution_id: str, email: str) -> dict | None:
    """Find a user by email within an institution.

    Email lives on user_profiles (PII is separated from the pseudonymous
    users row), so this is a join done in two steps rather than one query.
    The institution filter is load-bearing: emails are not globally unique,
    and resolving across tenants would be a serious isolation bug.

    If SEVERAL profiles share the email (the duplicate-account state this
    whole change exists to repair), the deterministic choice is the
    OLDEST account.
    """
    normalized = email.strip().lower()
    if not normalized:
        return None
    profiles = select("user_profiles", {
        "email": f"ilike.{normalized}", "select": "user_id",
    })
    if not profiles:
        return None
    ids = [p["user_id"] for p in profiles]
    users = select("users", {
        "id": f"in.({','.join(ids)})",
        "institution_id": f"eq.{institution_id}",
        "select": "id,institution_id,lms_user_id,role,created_at",
        "order": "created_at.asc",
    })
    return users[0] if users else None


def _touch_profile(*, user_id: str, display_name: str | None, email: str | None) -> None:
    """Refresh the profile with whatever the current call knows, without
    clobbering a known value with a missing one."""
    values: dict = {}
    if display_name:
        values["display_name"] = display_name
    if email:
        values["email"] = email
    if values:
        upsert("user_profiles", [{"user_id": user_id, **values}], on_conflict="user_id")


def upsert_user(*, institution_id: str, lms_user_id: str, role: str,
                display_name: str | None, email: str | None) -> dict:
    """DEPRECATED for identity resolution — use `resolve_user`.

    Kept because it is the raw (institution, lms_user_id) upsert and some
    callers legitimately want exactly that. Every path that resolves a PERSON
    (the LTI launch, the roster sync) must call resolve_user instead: this
    function will happily create a second row for someone who already exists
    under the other identifier form, which is the duplicate-account bug.
    """
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


def get_or_create_course(*, institution_id: str, lms_course_id: str, title: str,
                         lms_course_external_id: str | None = None) -> dict:
    """Upsert the course, recording the LMS external id it was resolved FROM.

    `lms_course_external_id` is what the LTI launch carries and what
    `resolve_course_ref` costs a Blackboard REST call to turn into
    `lms_course_id`. Persisting it here — on the same row that already holds the
    resolved id — is what lets a later launch skip that call entirely
    (course_by_lms_external_id below).

    Only written when the caller actually resolved it. A caller that passed an
    already-known course straight through (having found it locally) has no need
    to re-resolve, but re-sending the same value is harmless and keeps this a
    single upsert path.
    """
    row = {
        "institution_id": institution_id,
        "lms_course_id": lms_course_id,
        "title": title,
    }
    if lms_course_external_id is not None:
        row["lms_course_external_id"] = lms_course_external_id
    rows = upsert("courses", [row], on_conflict="institution_id,lms_course_id")
    return rows[0]


def course_by_lms_external_id(*, institution_id: str, lms_course_external_id: str) -> dict | None:
    """The course Kala already resolved for this LMS external id, or None.

    This is the whole of Fix 1's read path: one indexed local lookup that
    replaces a Blackboard REST call on every launch after the first.

    Defensive about the column existing at all. Migration 0016 adds
    `lms_course_external_id`, and until the user confirms it is applied the
    column is absent — PostgREST answers a select naming an unknown column with
    a 400, which would turn a missing migration into a BROKEN LAUNCH rather
    than a slow one. A failure here degrades to "not found" (the pre-fix
    behavior: resolve over REST), never to an exception that blocks the launch.
    """
    try:
        rows = select("courses", {
            "institution_id": f"eq.{institution_id}",
            "lms_course_external_id": f"eq.{lms_course_external_id}",
            "select": "id,institution_id,lms_course_id,title",
            "limit": "1",
        })
    except Exception:
        # Column not migrated yet, or a transient read failure. Either way the
        # caller falls back to the REST resolution path, which still works.
        return None
    return rows[0] if rows else None


def touch_course_sync_timestamp(*, course_id: str, column: str) -> None:
    """Stamp a successful roster sync / skill seed on the course row.

    `column` is validated against an allow-list rather than interpolated
    freely: it reaches PostgREST as a payload KEY, and a caller-supplied key
    from anywhere less trusted would be a write primitive. The two callers are
    both server-side constants, but the allow-list is what keeps that true if a
    third caller ever appears.

    Best-effort by contract: this is bookkeeping for a cooldown, and failing to
    record a timestamp must never surface as a failed sync — the sync itself
    already succeeded. Fails open (logs) so the next launch simply re-runs.
    """
    if column not in ("last_roster_sync_at", "last_skill_seed_at"):
        raise ValueError(f"refusing to stamp unknown column {column!r}")
    try:
        update("courses", {"id": f"eq.{course_id}"}, {
            column: datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        # Migration 0016 not applied yet, or a transient write failure. The
        # cooldown degrades to "never stamps" = always syncs, i.e. the
        # pre-fix behavior. Not an error worth failing a launch over.
        logger.warning("could not stamp %s on course %s; cooldown stays open", column, course_id)


def course_synced_within(*, course: dict, column: str, cooldown_seconds: int) -> bool:
    """True if `column` on this course is inside the cooldown window.

    Reads the timestamp straight off the course row the launch already
    fetched — no extra query. A null/absent timestamp means never synced, which
    is always "not within cooldown" (sync now), so the first launch after this
    migration always does the full work exactly as before.

    An unparseable or absent value also returns False, for the same fail-open
    reason as touch_course_sync_timestamp: the safe direction is to re-sync.
    """
    if column not in ("last_roster_sync_at", "last_skill_seed_at"):
        raise ValueError(f"refusing to read unknown column {column!r}")
    raw = (course or {}).get(column)
    if not raw:
        return False
    try:
        stamped = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamped.tzinfo is None:
        stamped = stamped.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamped).total_seconds() < cooldown_seconds


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
