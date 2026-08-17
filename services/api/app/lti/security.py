"""LTI 1.3 security primitives, written to be deterministic on Lambda:
  - verify_id_token: validate the platform's signed launch token against its
    JWKS (RS256), checking issuer, audience, expiry.
  - build_tool_jwks: expose the tool's public key so the platform can verify
    our client assertions (needed for AGS/NRPS service calls).
  - sign_state / verify_state: a short-lived signed cookie that carries the
    OIDC state and nonce between /lti/login and /lti/launch (no server session
    needed, which suits stateless Lambda).

PyLTI1p3 is available in requirements if you prefer the library's batteries
(NRPS, AGS, Deep Linking); this module keeps the launch path dependency-light
and easy to reason about."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import jwt
from cryptography.hazmat.primitives import serialization

from app.config import get_settings

_TOOL_KID = "kala-tool-key-1"
_jwk_clients: dict[str, jwt.PyJWKClient] = {}


def _jwk_client(url: str) -> jwt.PyJWKClient:
    client = _jwk_clients.get(url)
    if client is None:
        client = jwt.PyJWKClient(url)
        _jwk_clients[url] = client
    return client


def verify_id_token(id_token: str) -> dict:
    """Validate the platform-signed launch JWT and return its claims."""
    s = get_settings()
    signing_key = _jwk_client(s.lti_keyset_url).get_signing_key_from_jwt(id_token).key
    return jwt.decode(
        id_token,
        signing_key,
        algorithms=["RS256"],
        audience=s.lti_client_id,
        issuer=s.lti_issuer,
        options={"require": ["exp", "iat", "nonce"]},
    )


def build_tool_jwks() -> dict:
    """JWKS derived from the tool's private key, served at /lti/jwks."""
    s = get_settings()
    private_key = serialization.load_pem_private_key(
        s.lti_tool_private_key_pem.encode(), password=None
    )
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": _TOOL_KID, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


# ---- signed state cookie (OIDC state + nonce) -----------------------------

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_dec(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def sign_state(payload: dict, ttl_seconds: int = 600) -> str:
    s = get_settings()
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    raw = _b64u(json.dumps(body, separators=(",", ":")).encode())
    sig = hmac.new(s.supabase_jwt_secret.encode(), raw.encode(), hashlib.sha256).digest()
    return f"{raw}.{_b64u(sig)}"


def verify_state(token: str) -> dict:
    s = get_settings()
    raw, _, sig = token.partition(".")
    expected = hmac.new(s.supabase_jwt_secret.encode(), raw.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64u(expected), sig):
        raise ValueError("bad state signature")
    body = json.loads(_b64u_dec(raw))
    if body.get("exp", 0) < int(time.time()):
        raise ValueError("state expired")
    return body
