"""Run Lane F checks with no dotenv reads or external network access.

From the repo root:
  env -i PATH="$PATH" services/api/.venv/bin/python \
    services/api/tests/run_study_checks.py services/api/tests -q --tb=short

All path arguments must be absolute or relative to the caller's directory.
An ephemeral signing key supports mocked LTI tests and is never displayed.
"""
from __future__ import annotations

import os
import secrets
import socket
import sys
import tempfile
from pathlib import Path


def main() -> int:
    api_root = Path(__file__).resolve().parents[1]
    args = [str(Path(arg).resolve()) if not arg.startswith("-") and Path(arg).exists()
            else arg for arg in sys.argv[1:]]
    sys.path.insert(0, str(api_root))
    from app.config import Settings
    Settings.model_config["env_file"] = None
    os.environ["SUPABASE_JWT_SECRET"] = secrets.token_urlsafe(48)

    def no_connect(*_args, **_kwargs):
        raise AssertionError("network disabled for Lane F checks")

    socket.socket.connect = no_connect
    socket.create_connection = no_connect
    import pytest
    with tempfile.TemporaryDirectory(prefix="kala-lane-f-checks-") as isolated:
        os.chdir(isolated)
        return pytest.main(args or [str(api_root / "tests"), "-q", "--tb=short"])


if __name__ == "__main__":
    raise SystemExit(main())
