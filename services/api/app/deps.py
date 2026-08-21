"""Shared FastAPI dependencies: resolve the caller's session from the bearer
token and guard endpoints by role."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from app.lms.blackboard import BlackboardConnector
from app.security.jwt import verify_session_token


@dataclass
class CurrentUser:
    user_id: str
    institution_id: str
    app_role: str
    course_id: str | None = None


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
