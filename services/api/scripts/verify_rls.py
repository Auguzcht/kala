"""
Verifies RLS is actually doing its job on a live Supabase project, without
hand-typing curl commands each time.

Two real requests against the table you pass in:
  1. anon key, no Authorization header    -> should be denied
  2. anon key + a real session token       -> should succeed, likely empty

Needs SUPABASE_ANON_KEY in services/api/.env (this is the public anon key
from Project Settings > API, safe to have in a local dev .env, not the
service_role key). The app itself doesn't use this value, only this script
does, so it's kept separate from app/config.py on purpose.

Run from services/api with your real .env already in place:
    uv run python scripts/verify_rls.py                  # checks mastery_state
    uv run python scripts/verify_rls.py evidence_events   # checks a specific table
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.mock_lti_launch import mint_mock_session_token  # noqa: E402


def _check(label: str, table: str, base_url: str, anon_key: str, token: str | None):
    headers = {"apikey": anon_key}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = httpx.get(f"{base_url}/rest/v1/{table}", headers=headers, timeout=10.0)
    print(f"  {label}: {resp.status_code} {resp.text[:200]}")
    return resp


def main() -> None:
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    table = sys.argv[1] if len(sys.argv) > 1 else "mastery_state"

    if not supabase_url or "localhost" in supabase_url:
        print("SUPABASE_URL isn't set to a real project in .env, point it at your")
        print("actual Supabase project before running this (not the throwaway")
        print("localhost value used for offline testing).")
        return
    if not anon_key:
        print("SUPABASE_ANON_KEY isn't set. Add it to services/api/.env, it's the")
        print("public anon key from Project Settings > API (not service_role).")
        return

    print(f"Checking RLS on '{table}' at {supabase_url}\n")

    print("1. anon key, no session token (should be denied):")
    anon_resp = _check("no-token", table, supabase_url, anon_key, token=None)

    print("\n2. minting a real session via mock LTI launch...")
    try:
        token = mint_mock_session_token()
    except Exception as exc:
        print(f"   FAILED to mint a token: {exc}")
        print("   Fix the launch flow first (see mock_lti_launch.py), can't test")
        print("   authenticated access without a real token.")
        return

    print("\n3. anon key + real session token (should succeed, likely empty):")
    auth_resp = _check("with-token", table, supabase_url, anon_key, token=token)

    print("\n--- Verdict ---")
    anon_denied = anon_resp.status_code in (401, 403) or "42501" in anon_resp.text
    if anon_denied:
        print("PASS: anon alone was denied.")
    else:
        print(f"UNEXPECTED: anon alone got {anon_resp.status_code}, expected a denial.")
        print("If anon is getting real data back, that's a serious RLS gap, check")
        print("0002_rls.sql actually applied and the table has RLS enabled.")

    if auth_resp.status_code == 200:
        print("PASS: authenticated request succeeded.")
    else:
        print(f"UNEXPECTED: authenticated request got {auth_resp.status_code}, expected 200.")
        print("This might mean the role is missing table-level GRANTs, not just")
        print("RLS policies, GRANT and RLS are two separate gates in Postgres.")


if __name__ == "__main__":
    main()
