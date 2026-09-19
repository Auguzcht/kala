"""Shared FastAPI dependencies: resolve the caller's session from the bearer
token and guard endpoints by role."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Path, status

from app.lms.blackboard import BlackboardConnector
from app.security.jwt import verify_session_token


@dataclass
class CurrentUser:
    user_id: str
    institution_id: str
    app_role: str
    course_id: str | None = None


def _validated_uuid(value: str) -> str:
    """Shared body: is this a well-formed UUID? Used by the deps below.

    Shape only. The two-layer staff gate still proves the caller may touch the
    row; this just stops Postgres's `22P02 invalid input syntax for type uuid`
    escaping as an unhandled `httpx.HTTPStatusError` and surfacing as a bare
    500. The message never echoes the value back — a malformed id is often a
    near-miss for a real one, and reflecting it into a body is a needless way
    to confirm a guess.
    """
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return value


# One dependency per UUID path-param NAME. A single generic dep cannot work:
# FastAPI resolves a dependency's own parameters from the request, and a bare
# `value: str` is read as a REQUIRED QUERY PARAM (422), not as the path value
# it is meant to guard. Binding the name with Path(..., alias=...) is what
# makes each dep receive the right path segment.
#
# Why 404 rather than letting FastAPI's native uuid.UUID annotation return 422:
# CONTRACT CONSISTENCY, not secrecy. Every failure mode on a course-scoped
# path should look identical to a client — a malformed id, a nonexistent id,
# and a real id the caller cannot access should all be one indistinguishable
# 404, so the frontend has a single case to handle instead of three. This is
# deliberately NOT the `_assert_teaches_course` 403-vs-404 argument, which is
# about not revealing whether a resource exists; rejecting garbage input
# before any lookup reveals nothing, since the caller typed the string.
#
# Used as a SIGNATURE default, never called inline:
#     def route(course_id: str = Depends(require_valid_course_id)):
# A body call would have to be repeated in every handler, so the 46th route
# someone adds next month forgets it. As a signature default it cannot be
# omitted while the path param is still declared, and it runs BEFORE the
# handler, the same way a native annotation would.

def require_valid_course_id(course_id: str = Path(...)) -> str:
    return _validated_uuid(course_id)


def require_valid_set_id(set_id: str = Path(...)) -> str:
    return _validated_uuid(set_id)


def require_valid_skill_id(skill_id: str = Path(...)) -> str:
    return _validated_uuid(skill_id)


def require_valid_user_id(user_id: str = Path(...)) -> str:
    return _validated_uuid(user_id)


def require_valid_column_id(column_id: str = Path(...)) -> str:
    return _validated_uuid(column_id)


def require_valid_conversation_id(conversation_id: str = Path(...)) -> str:
    return _validated_uuid(conversation_id)


def require_valid_step_id(step_id: str = Path(...)) -> str:
    return _validated_uuid(step_id)


def require_valid_rec_id(rec_id: str = Path(...)) -> str:
    return _validated_uuid(rec_id)


def require_valid_attachment_id(attachment_id: str = Path(...)) -> str:
    return _validated_uuid(attachment_id)


# The set of (path param name -> dependency), so the signature rewrite is
# table-driven rather than a chain of ifs.
UUID_PATH_DEPS = {
    "course_id": "require_valid_course_id",
    "set_id": "require_valid_set_id",
    "skill_id": "require_valid_skill_id",
    "user_id": "require_valid_user_id",
    "column_id": "require_valid_column_id",
    "conversation_id": "require_valid_conversation_id",
    "step_id": "require_valid_step_id",
    "rec_id": "require_valid_rec_id",
    "attachment_id": "require_valid_attachment_id",
}


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = verify_session_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    return CurrentUser(
        user_id=claims["sub"],
        institution_id=claims.get("institution_id", ""),
        app_role=claims.get("app_role", ""),
        course_id=claims.get("course_id"),
    )


def require_role(*roles: str):
    def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.app_role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user

    return _guard


@lru_cache
def get_lms_connector() -> BlackboardConnector:
    return BlackboardConnector()
