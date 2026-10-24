"""Shared API/worker pytest isolation (APPROVAL-02 section 5, APPROVAL-03).

Loaded before either service's test modules. Run each suite in its own process
from its service directory; both services intentionally use the package `app`.
Only pytest loads this file; application startup and deployments are unaffected.
"""
from __future__ import annotations

import os
import secrets
import socket

import pytest

_isolation = pytest.MonkeyPatch()

# Discard inherited configuration by name, without displaying its values.
# In particular, no inherited Secrets Manager ARN or AWS profile may bootstrap
# hosted settings during test collection. Tests can still override fake settings.
_application_prefixes = (
    "AWS_", "KALA_", "SUPABASE_", "OPENAI_", "OPENROUTER_", "BEDROCK_",
    "LTI_", "LMS_", "BANK_",
)
_application_names = {
    "AI_PROVIDER", "EMBED_PROVIDER", "FRONTEND_URL", "SESSION_TTL_SECONDS",
    "SKILL_SEED_ON_LAUNCH", "WORKER_FUNCTION_ARN", "TRACER_K",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
}
for _name in tuple(os.environ):
    if _name.startswith(_application_prefixes) or _name in _application_names:
        _isolation.delenv(_name)

for _name, _value in {
    "SUPABASE_URL": "http://supabase.test",
    "SUPABASE_SERVICE_KEY": "test-only-service-key",
    "SUPABASE_JWT_SECRET": secrets.token_urlsafe(48),
    "OPENAI_API_KEY": "test-only-openai-key",
    "OPENROUTER_API_KEY": "test-only-openrouter-key",
    "AWS_ACCESS_KEY_ID": "test-only-access-key",
    "AWS_SECRET_ACCESS_KEY": "test-only-secret-key",
    "AWS_DEFAULT_REGION": "ap-southeast-1",
    "AWS_REGION": "ap-southeast-1",
    "AWS_EC2_METADATA_DISABLED": "true",
    "PYTHON_DOTENV_DISABLED": "1",
}.items():
    _isolation.setenv(_name, _value)
del _value  # Do not retain the generated signing value as a module attribute.


class _NoNetworkSocket(socket.socket):
    """Keep Unix socket pairs for asyncio, reject all IPv4/IPv6 sockets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.family in (socket.AF_INET, socket.AF_INET6):
            self.close()
            raise AssertionError("Network sockets are disabled in tests; mock the service boundary")


def _no_network(*_args, **_kwargs):
    raise AssertionError("Network access is disabled in tests; mock the service boundary")


_isolation.setattr(socket, "socket", _NoNetworkSocket)
for _name in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
    _isolation.setattr(socket, _name, _no_network)

# Importing this module only defines Settings and its lazy loader. Fake env and
# socket guards are already installed; disable dotenv before any Settings call.
from app.config import Settings, get_settings

_isolation.setitem(Settings.model_config, "env_file", None)
get_settings.cache_clear()


def pytest_unconfigure(config):
    """Release process-wide patches after all tests and report hooks finish."""
    get_settings.cache_clear()
    _isolation.undo()
