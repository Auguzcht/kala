"""AI-REQ-002: safe attempt correlation, fallback diagnosis and compatibility."""
import json
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from botocore.exceptions import ClientError

from app.ai import bedrock
from app.ai.errors import ModelUnavailableError
from app.ai.request_budget import RequestBudget, TutorTimeout

MARKER = "synthetic-sensitive-exception-body-and-prompt"


def _events(caplog):
    return [json.loads(record.getMessage().removeprefix("tutor_provider_error "))
            for record in caplog.records if record.getMessage().startswith("tutor_provider_error ")]


@pytest.fixture
def settings(monkeypatch):
    settings = SimpleNamespace(ai_provider="openrouter", openrouter_model_fallback="fallback",
                               openai_embed_model="embedding", bedrock_embed_model="embedding")
    monkeypatch.setattr(bedrock, "get_settings", lambda: settings)
    return settings


@pytest.mark.parametrize("fallback_status", (401, 402, 403, 503, None))
def test_AI_REQ_002_fallback_logs_its_own_model_and_status(monkeypatch, caplog, settings, fallback_status):
    calls, sleeps = [], []

    def post(**kwargs):
        calls.append(kwargs["model_id"])
        status = 429 if len(calls) == 1 else fallback_status
        if status is None:
            raise httpx.ReadTimeout(MARKER)
        httpx.Response(status, request=httpx.Request("POST", "https://provider.test/api"),
                       text=MARKER).raise_for_status()

    monkeypatch.setattr(bedrock, "_openrouter_post", post)
    monkeypatch.setattr(bedrock.time, "sleep", sleeps.append)
    budget = RequestBudget()
    with pytest.raises(ModelUnavailableError) as caught:
        bedrock.converse(model_id="primary", system=MARKER, messages=[], budget=budget)
    assert calls == ["primary", "fallback"]
    assert sleeps == [1.5]
    assert caught.value.model_id == "fallback" and caught.value.status_code == fallback_status
    events = _events(caplog)
    assert [(event["model"], event["http_status"]) for event in events] == [("primary", 429), ("fallback", fallback_status)]
    assert {event["request_id"] for event in events} == {budget.request_id}
    assert {event["provider"] for event in events} == {"openrouter"}
    assert {event["stage"] for event in events} == {"chat"}
    assert MARKER not in caplog.text


def test_AI_REQ_002_request_ids_stable_across_stages_and_distinct_across_requests(monkeypatch, caplog, settings):
    def fail(**kwargs):
        raise httpx.ConnectError(MARKER)

    monkeypatch.setattr(bedrock, "_openrouter_post", fail)

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): fail()

    monkeypatch.setattr(bedrock, "_openai_client", lambda **kwargs: Client())
    first, second = RequestBudget(), RequestBudget()
    assert UUID(first.request_id).version == UUID(second.request_id).version == 4
    assert first.request_id != second.request_id
    for operation in [
        lambda: bedrock._openai_embed(MARKER, input_type="search_query", budget=first),
        lambda: bedrock._openrouter_converse(model_id="primary", system=MARKER, messages=[], max_tokens=2048, budget=first),
        lambda: bedrock._openrouter_converse(model_id="primary", system=MARKER, messages=[], max_tokens=2048, budget=second),
    ]:
        with pytest.raises(ModelUnavailableError):
            operation()
    events = _events(caplog)
    assert [event["stage"] for event in events] == ["embed", "chat", "chat"]
    assert [event["request_id"] for event in events] == [first.request_id, first.request_id, second.request_id]
    assert all(event["http_status"] is None for event in events)
    assert MARKER not in caplog.text


@pytest.mark.parametrize("stage", ("embed", "chat"))
@pytest.mark.parametrize("status", (403, None))
def test_AI_REQ_002_bedrock_sdk_failures_keep_original_mapping(monkeypatch, caplog, settings, stage, status):
    failure = (ClientError({"Error": {"Code": "AccessDeniedException", "Message": MARKER},
                            "ResponseMetadata": {"HTTPStatusCode": status}}, "test")
               if status is not None else RuntimeError(MARKER))

    def fail(**kwargs):
        raise failure

    monkeypatch.setattr(bedrock, "_bedrock_runtime", lambda **kwargs: SimpleNamespace(
        invoke_model=fail, converse=fail,
    ))
    budget = RequestBudget()
    if stage == "embed":
        with pytest.raises(type(failure)) as caught:
            bedrock._bedrock_embed(MARKER, input_type="search_query", budget=budget)
        assert caught.value is failure  # Previously unwrapped: still unwrapped.
    else:
        with pytest.raises(ModelUnavailableError) as caught:
            bedrock._bedrock_converse(model_id="chat", system=MARKER, messages=[], max_tokens=2048, budget=budget)
        assert caught.value.__cause__ is failure
        assert caught.value.status_code is None  # Do not alter existing response/error mapping.
    assert _events(caplog) == [{
        "stage": stage, "provider": "bedrock", "model": "embedding" if stage == "embed" else "chat",
        "http_status": status, "request_id": budget.request_id,
        "error_code": "forbidden" if status == 403 else "provider_error",
    }]
    assert MARKER not in caplog.text


@pytest.mark.parametrize("provider", ("openai", "openrouter"))
def test_AI_REQ_002_unwrapped_embedding_parse_error_stays_unwrapped(monkeypatch, caplog, settings, provider):
    settings.openrouter_embed_model = "embedding"
    failure = ValueError(MARKER)

    class Response:
        def raise_for_status(self): pass
        def json(self): raise failure

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): return Response()

    monkeypatch.setattr(bedrock, f"_{provider}_client", lambda **kwargs: Client())
    budget = RequestBudget()
    with pytest.raises(ValueError) as caught:
        getattr(bedrock, f"_{provider}_embed")(MARKER, input_type="search_query", budget=budget)
    assert caught.value is failure
    assert _events(caplog)[0]["http_status"] is None
    assert _events(caplog)[0]["model"] == "embedding"
    assert MARKER not in caplog.text


def test_AI_REQ_002_unwrapped_chat_response_shape_stays_unwrapped(monkeypatch, caplog, settings):
    monkeypatch.setattr(bedrock, "_openrouter_post", lambda **kwargs: {"choices": [None]})
    with pytest.raises(AttributeError):
        bedrock._openrouter_converse(model_id="chat", system=MARKER, messages=[], max_tokens=2048, budget=RequestBudget())
    assert _events(caplog)[0]["model"] == "chat"
    assert _events(caplog)[0]["http_status"] is None
    assert MARKER not in caplog.text


def test_AI_REQ_002_deadline_exception_does_not_become_provider_error(monkeypatch, caplog, settings):
    failure = TutorTimeout()

    def post(**kwargs):
        raise failure

    monkeypatch.setattr(bedrock, "_openrouter_post", post)
    with pytest.raises(TutorTimeout) as caught:
        bedrock._openrouter_converse(model_id="chat", system=MARKER, messages=[], max_tokens=2048, budget=RequestBudget())
    assert caught.value is failure
    assert _events(caplog) == []


def test_AI_REQ_002_nonbudgeted_failures_keep_existing_diagnostics(monkeypatch, caplog, settings):
    def post(**kwargs):
        httpx.Response(401, request=httpx.Request("POST", "https://provider.test/api")).raise_for_status()

    monkeypatch.setattr(bedrock, "_openrouter_post", post)
    with pytest.raises(ModelUnavailableError) as caught:
        bedrock._openrouter_converse(model_id="chat", system="system", messages=[], max_tokens=2048)
    assert caught.value.status_code == 401
    assert _events(caplog) == []
    assert "OpenRouter chat request failed (model=chat, status=401)" in caplog.text
