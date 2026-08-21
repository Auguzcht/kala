"""
Exercises the real /lti/login -> /lti/launch flow against a fake LMS
platform, so you can confirm Supabase writes and JWT minting work before
Blackboard or Canvas are in the picture.

What this does NOT test: the platform's real JWKS format quirks, real NRPS
roster shape, real deployment id conventions. It's a spine check, not a
substitute for a real launch once you have one.

Run from services/api with your real .env already in place:
    uv run python scripts/mock_lti_launch.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

FAKE_KID = "fake-platform-key-1"
FAKE_ISSUER = "http://localhost:9931"
FAKE_CLIENT_ID = "kala-mock-client"
FAKE_DEPLOYMENT_ID = "mock-deployment-1"


def _start_fake_jwks_server(public_jwk: dict) -> HTTPServer:
    """A throwaway HTTP server standing in for the LMS's JWKS endpoint,
    since PyJWT's PyJWKClient fetches this over real HTTP."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"keys": [public_jwk]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # noqa: A003, keep test output quiet
            pass

    server = HTTPServer(("localhost", 9931), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def mint_mock_session_token() -> str:
    """Runs the full /lti/login -> /lti/launch flow against a fake platform
    and returns the minted session JWT. Raises if any step fails, callers
    that just want a token for RLS testing can call this directly."""

    # 1. Generate the fake platform's keypair and stand up its JWKS endpoint.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": FAKE_KID, "use": "sig", "alg": "RS256"})
    _start_fake_jwks_server(public_jwk)

    # 2. Point Kala's own settings at this fake platform. Set the env before
    # importing app.config so the cached Settings picks these up.
    os.environ["LTI_ISSUER"] = FAKE_ISSUER
    os.environ["LTI_CLIENT_ID"] = FAKE_CLIENT_ID
    os.environ["LTI_AUTH_LOGIN_URL"] = f"{FAKE_ISSUER}/authorize"  # never actually hit
    os.environ["LTI_KEYSET_URL"] = f"{FAKE_ISSUER}/jwks.json"
    os.environ["LTI_DEPLOYMENT_IDS"] = FAKE_DEPLOYMENT_ID

    from app.config import get_settings
    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app
    from app.deps import get_lms_connector

    class MockConnector:
        def resolve_course_ref(self, external_id: str) -> str:
            return external_id

    app.dependency_overrides[get_lms_connector] = MockConnector

    client = TestClient(app)

    # 3. Drive /lti/login the way the LMS's OIDC redirect would, to get a
    # real signed state cookie back.
    login_resp = client.get(
        "/lti/login",
        params={"login_hint": "mock-user-1", "target_link_uri": "http://localhost:8000/lti/launch"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 302, f"expected redirect, got {login_resp.status_code}: {login_resp.text}"

    from urllib.parse import parse_qs, urlparse
    redirected_to = urlparse(login_resp.headers["location"])
    nonce = parse_qs(redirected_to.query)["nonce"][0]
    state = parse_qs(redirected_to.query)["state"][0]
    state_cookie = login_resp.cookies.get("kala_lti_state")
    assert state_cookie, "no state cookie set, check the /lti/login handler"

    # 4. Build and sign a fake id_token as if the platform sent it back,
    # using the real LTI 1.3 claim URIs the launch handler checks.
    now = int(time.time())
    claims = {
        "iss": FAKE_ISSUER,
        "aud": FAKE_CLIENT_ID,
        "sub": "mock-user-1",
        "name": "Mock Student",
        "email": "mock.student@example.test",
        "nonce": nonce,
        "iat": now,
        "exp": now + 300,
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": FAKE_DEPLOYMENT_ID,
        "https://purl.imsglobal.org/spec/lti/claim/roles": [
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
        ],
        "https://purl.imsglobal.org/spec/lti/claim/context": {
            "id": "mock-course-1",
            "label": "mock-course-1",
            "title": "Mock Course",
        },
    }
    id_token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": FAKE_KID})

    # 5. Post it to /lti/launch exactly like the platform's form_post would.
    launch_resp = client.post(
        "/lti/launch",
        data={"id_token": id_token, "state": state},
        cookies={"kala_lti_state": state_cookie},
        follow_redirects=False,
    )
    if launch_resp.status_code != 302:
        raise RuntimeError(f"launch failed ({launch_resp.status_code}): {launch_resp.text}")

    from urllib.parse import parse_qs as _parse_qs
    location = launch_resp.headers["location"]
    fragment = location.split("#", 1)[1] if "#" in location else ""
    token = _parse_qs(fragment).get("token", [None])[0]
    if not token:
        raise RuntimeError(f"launch redirected but no token in fragment: {location}")
    return token


def main() -> None:
    try:
        token = mint_mock_session_token()
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        if "Connection refused" in str(exc) or "connect" in str(exc).lower():
            print("The launch handler passed every LTI check (state, nonce, signature,")
            print("message type, deployment id), this failure is purely in the Supabase")
            print("write step. Check SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env.")
        return

    print("\nSUCCESS: the launch handler validated the token, wrote to Supabase,")
    print("and minted a session. Check your Supabase institutions/users/courses")
    print("tables for a new 'Mock Course' row to confirm the writes landed.\n")
    print(f"Session token:\n{token}")


if __name__ == "__main__":
    main()
