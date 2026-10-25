"""Read-only, scoped evidence keysets (TWIN-REQ-010 / INSTR-REQ-010)."""
from __future__ import annotations

import base64
import hmac
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db import supabase as db


class HistoryEvent(BaseModel):
    id: str
    type: str
    correct: bool | None
    latencyMs: int | None = None
    skillName: str
    createdAt: str | None = None


class EvidenceHistoryPage(BaseModel):
    courseId: str
    evidence: list[HistoryEvent]
    nextCursor: str | None = None


def _key() -> bytes:
    secret = get_settings().supabase_jwt_secret
    if not secret:
        raise RuntimeError("evidence cursor signing is unavailable")
    return hmac.digest(secret.encode(), b"kala:evidence-history:v1", "sha256")


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(value: str) -> bytes:
    raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    if _encode(raw) != value:
        raise ValueError("noncanonical encoding")
    return raw


def _scope(*, institution_id: str, caller_id: str, user_id: str, course_id: str) -> list[str]:
    return [str(UUID(value)) for value in (institution_id, caller_id, user_id, course_id)]


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    # A canonical ISO timestamp cannot inject PostgREST filter syntax.
    return parsed.isoformat()


def _cursor(*, scope: list[str], row: dict) -> str:
    raw = json.dumps({"v": 1, "s": scope, "t": _timestamp(row["created_at"]),
                      "id": str(UUID(row["id"]))}, separators=(",", ":")).encode()
    return _encode(raw) + "." + _encode(hmac.digest(_key(), raw, "sha256"))


def _cutoff(cursor: str, scope: list[str]) -> tuple[str, str]:
    try:
        if not cursor or len(cursor) > 2048:
            raise ValueError("invalid length")
        payload, signature = cursor.split(".")
        raw = _decode(payload)
        if not hmac.compare_digest(_decode(signature), hmac.digest(_key(), raw, "sha256")):
            raise ValueError("signature")
        data = json.loads(raw)
        if (not isinstance(data, dict) or set(data) != {"v", "s", "t", "id"}
                or type(data["v"]) is not int or data["v"] != 1 or data["s"] != scope):
            raise ValueError("scope or version")
        return _timestamp(data["t"]), str(UUID(data["id"]))
    except (ValueError, TypeError, AttributeError, KeyError, UnicodeError):
        raise HTTPException(422, "invalid evidence cursor") from None


def history_page(*, institution_id: str, caller_id: str, user_id: str, course_id: str,
                 cursor: str | None = None, limit: int = 25) -> dict:
    """Call only after route authorization; repeat tenant/user/course predicates.

    A signed cutoff remains valid after identity repair reattributes its anchor.
    No writes, anchor lookup, counts, offsets, or model calls are performed.
    """
    if type(limit) is not int or not 1 <= limit <= 100:
        raise HTTPException(422, "invalid evidence limit")
    scope = _scope(institution_id=institution_id, caller_id=caller_id,
                   user_id=user_id, course_id=course_id)
    params = {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}",
        "select": "id,skill_id,type,correct,latency_ms,created_at",
        "order": "created_at.desc,id.desc", "limit": str(limit + 1),
    }
    if cursor is not None:
        timestamp, event_id = _cutoff(cursor, scope)
        params["or"] = f"(created_at.lt.{timestamp},and(created_at.eq.{timestamp},id.lt.{event_id}))"
    rows = db.select("evidence_events", params)
    events = rows[:limit]
    # Look up names only for this page, including evidence for removed/unapproved skills.
    # Names are restricted to approved skills, preserving the existing Twin boundary.
    skill_ids = sorted({str(UUID(e["skill_id"])) for e in events if e.get("skill_id")})
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved", "id": f"in.({','.join(skill_ids)})", "select": "id,name",
    }) if skill_ids else []
    names = {s["id"]: s["name"] for s in skills}
    return {
        "courseId": course_id,
        "evidence": [{"id": e["id"], "type": e["type"], "correct": e["correct"],
                      "latencyMs": e.get("latency_ms"),
                      "skillName": names.get(e.get("skill_id"), "Unknown skill"),
                      "createdAt": e["created_at"]} for e in events],
        "nextCursor": _cursor(scope=scope, row=events[-1]) if len(rows) > limit else None,
    }
