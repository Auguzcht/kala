"""The single session token. After a valid LTI launch the backend mints this
HS256 token with the Supabase JWT secret. It is accepted by BOTH:
  - Supabase (so the browser can read RLS-protected rows directly), and
  - this API (so feature endpoints can authorize the caller).
Claims carry the tenant and role that the database RLS reads:
  sub          -> users.id  (auth.uid())
  institution_id, app_role   (read by the RLS helper functions)
  role='authenticated', aud='authenticated'  (required by Supabase)."""
from __future__ import annotations

import time
import uuid

import jwt

from app.config import get_settings


def mint_session_token(
    *,
    user_id: str,
    institution_id: str,
    app_role: str,
    course_id: str | None = None,
    display_name: str | None = None,
) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "app_role": app_role,
        "institution_id": institution_id,
        "iat": now,
        "exp": now + s.session_ttl_seconds,
        "jti": str(uuid.uuid4()),
    }
    if course_id:
        payload["course_id"] = course_id
    if display_name:
        payload["display_name"] = display_name
    return jwt.encode(payload, s.supabase_jwt_secret, algorithm="HS256")


def verify_session_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(
        token,
        s.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )
