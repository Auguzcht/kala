"""APPROVAL-05 Lane X: offline evidence, not a provider-recovery claim.

Uses committed services/conftest.py isolation. No credentials, dotenv reads,
real provider requests, or production behavior changes. TUTOR-REQ-001 / WI-01.
"""
import json
from types import SimpleNamespace

import httpx
import pytest
from conftest import COURSE_ID, INSTITUTION_ID, USER_ID
from fastapi.testclient import TestClient

from app.ai import bedrock
from app.ai.errors import ModelUnavailableError
from app.ai.request_budget import RequestBudget, TutorTimeout
from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import tutor

HTTP_FAILURES = (301, 400, 401, 402, 403, 404, 408, 409, 422, 429, 500, 502, 503, 504, 529)
FALLBACK_STATUSES = {404, 408, 429, 500, 502, 503, 504}
SAFE_DETAIL = "Kala's model provider is unavailable right now. Please try again."
SENSITIVE_MARKER = "synthetic-sensitive-provider-text"


def _response(status):
    return httpx.Response(status, request=httpx.Request("POST", "https://provider.test/api"),
                          text=SENSITIVE_MARKER)


@pytest.mark.parametrize("status", (None, *HTTP_FAILURES))
@pytest.mark.parametrize("stage", ("openrouter_chat", "openrouter_embed", "openai_embed"))
def test_AI_REQ_002_provider_failure_metadata(monkeypatch, caplog, status, stage):
    """Error metadata survives conversion and is emitted without raw data."""
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        openrouter_embed_model="investigation-embedding", openai_embed_model="investigation-embedding",
    ))
    response = _response(status) if status is not None else None

    def fail_transport():
        raise httpx.ReadTimeout(SENSITIVE_MARKER)

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            if response is None:
                fail_transport()
            return response

    budget = RequestBudget()
    if stage == "openrouter_chat":
        def post(**kwargs):
            if response is None:
                fail_transport()
            response.raise_for_status()

        monkeypatch.setattr(bedrock, "_openrouter_post", post)
        operation = lambda: bedrock._openrouter_converse(
            model_id="investigation-chat", system=SENSITIVE_MARKER, messages=[], max_tokens=2048, budget=budget,
        )
        expected_model = "investigation-chat"
    else:
        provider = stage.removesuffix("_embed")
        monkeypatch.setattr(bedrock, f"_{provider}_client", lambda **kwargs: Client())
        operation = lambda: getattr(bedrock, f"_{provider}_embed")(
            SENSITIVE_MARKER, input_type="search_query", budget=budget,
        )
        expected_model = "investigation-embedding"

    with pytest.raises(ModelUnavailableError) as caught:
        operation()
    assert caught.value.status_code == status
    assert caught.value.provider == ("openai" if stage == "openai_embed" else "openrouter")
    assert caught.value.model_id == expected_model
    assert caught.value.model_not_found == (status == 404)
    assert str(caught.value) == SAFE_DETAIL
    diagnostics = [record for record in caplog.records if record.getMessage().startswith("tutor_provider_error ")]
    assert len(diagnostics) == 1
    assert diagnostics[0].levelname == "ERROR"
    assert json.loads(diagnostics[0].getMessage().removeprefix("tutor_provider_error ")) == {
        "stage": "chat" if stage == "openrouter_chat" else "embed",
        "provider": caught.value.provider,
        "model": expected_model,
        "http_status": status,
        "request_id": budget.request_id,
        "error_code": {401: "unauthorized", 402: "payment_required", 403: "forbidden"}.get(status, "provider_error"),
    }
    assert SENSITIVE_MARKER not in caplog.text


@pytest.mark.parametrize("status", (None, *HTTP_FAILURES))
def test_TUTOR_REQ_001_investigation_chat_fallback_decision(monkeypatch, status):
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        ai_provider="openrouter", openrouter_model_fallback="global-fallback",
    ))
    calls, sleeps = [], []
    failure = ModelUnavailableError(SAFE_DETAIL, provider="openrouter", model_id="primary", status_code=status)

    def converse(**kwargs):
        calls.append(kwargs["model_id"])
        if len(calls) == 1:
            raise failure
        return "fallback answer"

    monkeypatch.setattr(bedrock, "_openrouter_converse", converse)
    monkeypatch.setattr(bedrock.time, "sleep", sleeps.append)
    budget = RequestBudget()
    options = {"model_id": "primary", "system": "system", "messages": [],
               "fallback_model_id": "role-fallback", "budget": budget}
    eligible = status is None or status in FALLBACK_STATUSES
    if eligible:
        assert bedrock.converse(**options) == "fallback answer"
    else:
        with pytest.raises(ModelUnavailableError) as caught:
            bedrock.converse(**options)
        assert caught.value is failure
    assert calls == (["primary", "role-fallback"] if eligible else ["primary"])
    assert sleeps == ([1.5] if status in {429, 503} else [])
    assert budget.fallback_used == eligible


def test_TUTOR_REQ_001_investigation_exact_fallback_status_set():
    """No hidden retry for payment/auth failures or unlisted 5xx statuses."""
    actual = {
        status for status in range(100, 600)
        if bedrock._can_fallback(ModelUnavailableError(
            SAFE_DETAIL, provider="openrouter", model_id="synthetic", status_code=status,
        ))
    }
    assert actual == FALLBACK_STATUSES


@pytest.mark.parametrize("failure_stage", ("retrieval", "chat"))
@pytest.mark.parametrize("failure_kind", ("provider", "deadline"))
def test_TUTOR_REQ_001_investigation_ask_502_vs_503(monkeypatch, caplog, failure_stage, failure_kind):
    """An upstream 503 maps to app 502; TutorTimeout maps to app 503."""
    user = CurrentUser(user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student")
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: user)
    calls = []

    def retrieve(**kwargs):
        calls.append("retrieval")
        if failure_stage == "retrieval":
            fail()
        return []

    def answer(**kwargs):
        calls.append("chat")
        fail()

    def fail():
        if failure_kind == "deadline":
            raise TutorTimeout()
        raise ModelUnavailableError(
            SAFE_DETAIL, provider="openrouter", model_id="synthetic", status_code=503,
        )

    monkeypatch.setattr(tutor.rag, "retrieve", retrieve)
    monkeypatch.setattr(tutor.model_router, "answer", answer)
    with TestClient(app) as client:
        response = client.post("/tutor/ask", json={"course_id": COURSE_ID, "question": "synthetic"})
    if failure_kind == "deadline":
        assert response.status_code == 503
        assert response.json() == {"detail": str(TutorTimeout()), "code": "tutor_timeout"}
    else:
        assert response.status_code == 502
        assert response.json() == {"detail": SAFE_DETAIL}
    assert calls == (["retrieval"] if failure_stage == "retrieval" else ["retrieval", "chat"])
    timing = [record.getMessage() for record in caplog.records if record.getMessage().startswith("tutor_timing ")]
    assert len(timing) == 1
    assert f"'outcome': '{'timeout' if failure_kind == 'deadline' else 'provider_error'}'" in timing[0]
