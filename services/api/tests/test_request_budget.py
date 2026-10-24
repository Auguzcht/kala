"""APPROVAL-01: TUTOR-REQ-001 and opt-in non-tutor compatibility."""
import time
from types import SimpleNamespace

import anyio
import httpx
import pytest
from app.ai import bedrock, rag, router
from app.ai.errors import ModelUnavailableError
from app.ai.request_budget import RequestBudget, TutorTimeout
from app.db import supabase as db


def test_TUTOR_REQ_001_budget_uses_one_deadline_and_reserve(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("app.ai.request_budget.monotonic", lambda: clock[0])
    budget = RequestBudget()
    assert budget.timeout(60) == 23
    assert budget.timeout(20) == 20
    clock[0] += 10
    assert budget.timeout(25) == 13
    clock[0] += 13
    with pytest.raises(TutorTimeout):
        budget.timeout(60)


def test_TUTOR_REQ_001_elapsed_guard_abandons_trickling_sync_operation():
    finished = []

    def trickle(*, budget):
        # Keeps producing activity: an inactivity timeout alone cannot bound it.
        for _ in range(12):
            time.sleep(0.01)
        finished.append(True)
        return "late"

    async def scenario():
        budget = RequestBudget(seconds=0.09, reserve=0.03)
        started = time.monotonic()
        with pytest.raises(TutorTimeout):
            await budget.run("chat", trickle)
        assert time.monotonic() - started < 0.11
        assert not finished
        assert budget.remaining() == 0
        await anyio.sleep(0.1)  # finish only this test's abandoned worker
        assert finished

    anyio.run(scenario)


def test_TUTOR_REQ_001_slow_fallback_is_skipped_below_six_seconds(monkeypatch):
    budget = RequestBudget()
    calls = []
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        ai_provider="openrouter", openrouter_model_fallback="fallback",
    ))

    def converse(**kwargs):
        calls.append(kwargs["model_id"])
        if kwargs["model_id"] == "primary":
            budget.deadline = time.monotonic() + 5.9
            raise ModelUnavailableError("down", provider="openrouter", model_id="primary", status_code=503)
        time.sleep(1)
        return "late fallback"

    monkeypatch.setattr(bedrock, "_openrouter_converse", converse)
    started = time.monotonic()
    with pytest.raises(TutorTimeout):
        bedrock.converse(model_id="primary", system="s", messages=[], budget=budget)
    assert calls == ["primary"]
    assert not budget.fallback_used
    assert time.monotonic() - started < 0.1


def test_TUTOR_REQ_001_fallback_backoff_cannot_cross_six_second_threshold(monkeypatch):
    budget = RequestBudget()
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        ai_provider="openrouter", openrouter_model_fallback="fallback",
    ))

    def primary(**kwargs):
        budget.deadline = time.monotonic() + 7
        raise ModelUnavailableError("down", provider="openrouter", model_id="primary", status_code=429)

    monkeypatch.setattr(bedrock, "_openrouter_converse", primary)
    monkeypatch.setattr(bedrock.time, "sleep", lambda _: pytest.fail("backoff cannot fit"))
    with pytest.raises(TutorTimeout):
        bedrock.converse(model_id="primary", system="s", messages=[], budget=budget)


def test_TUTOR_REQ_001_fallback_records_actual_role(monkeypatch):
    budget = RequestBudget()
    calls = []
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        ai_provider="openrouter", openrouter_model_fallback="fallback",
    ))

    def converse(**kwargs):
        calls.append(kwargs["model_id"])
        if len(calls) == 1:
            raise ModelUnavailableError("down", provider="openrouter", model_id="primary", status_code=500)
        return "answer"

    monkeypatch.setattr(bedrock, "_openrouter_converse", converse)
    assert bedrock.converse(model_id="primary", system="s", messages=[], budget=budget) == "answer"
    assert calls == ["primary", "fallback"]
    assert budget.fallback_used and budget.provider_role == "chat_fallback"


@pytest.mark.parametrize("factory,current", [
    (db._client, 60), (bedrock._openrouter_client, 25), (bedrock._openai_client, 20),
])
def test_TUTOR_REQ_001_http_clients_default_unchanged_and_opt_in_clamped(monkeypatch, factory, current):
    captured = []
    monkeypatch.setattr(db, "get_settings", lambda: SimpleNamespace(
        supabase_url="https://db.example.test", supabase_service_key="fake",
    ))
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        openrouter_base_url="https://model.example.test", openrouter_api_key="fake",
        openai_base_url="https://embed.example.test", openai_api_key="fake",
    ))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: captured.append(kwargs))
    factory()
    factory(budget=RequestBudget(seconds=10))
    assert captured[0]["timeout"] == current
    assert 6.9 < captured[1]["timeout"] <= 7
    assert {k: v for k, v in captured[0].items() if k != "timeout"} == {
        k: v for k, v in captured[1].items() if k != "timeout"
    }


def test_TUTOR_REQ_001_bedrock_defaults_unchanged_and_opt_in_config(monkeypatch):
    import boto3

    calls = []
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(aws_region="test-region"))
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: calls.append((args, kwargs)))
    bedrock._bedrock_runtime()
    bedrock._bedrock_runtime(budget=RequestBudget(seconds=10))
    assert calls[0] == (("bedrock-runtime",), {"region_name": "test-region"})
    config = calls[1][1]["config"]
    assert 6.9 < config.read_timeout <= 7
    assert 6.9 < config.connect_timeout <= 7
    assert config.retries == {"total_max_attempts": 1}


def test_TUTOR_REQ_001_db_default_call_signature_and_payload_unchanged(monkeypatch):
    calls = []

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args, **kwargs):
            calls.append(("get", args, kwargs))
            return httpx.Response(200, json=[{"id": "fake"}], request=httpx.Request("GET", "https://example.test"))
        def post(self, *args, **kwargs):
            calls.append(("post", args, kwargs))
            return httpx.Response(200, json=[], request=httpx.Request("POST", "https://example.test"))
        def patch(self, *args, **kwargs):
            calls.append(("patch", args, kwargs))
            return httpx.Response(200, json=[], request=httpx.Request("PATCH", "https://example.test"))

    monkeypatch.setattr(db, "_client", lambda: Client())  # no new keyword on default path
    assert db.select("rows", {"id": "eq.fake"}) == [{"id": "fake"}]
    db.insert("rows", [{"text": "unchanged"}])
    db.update("rows", {"id": "eq.fake"}, {"text": "unchanged"})
    db.rpc("fn", {"arg": 1})
    assert calls == [
        ("get", ("/rows",), {"params": {"id": "eq.fake"}}),
        ("post", ("/rows",), {"json": [{"text": "unchanged"}], "headers": {"Prefer": "return=representation"}}),
        ("patch", ("/rows",), {"params": {"id": "eq.fake"}, "json": {"text": "unchanged"}, "headers": {"Prefer": "return=representation"}}),
        ("post", ("/rpc/fn",), {"json": {"arg": 1}}),
    ]


def test_AI_REQ_001_default_router_and_rag_copies_stay_unchanged(monkeypatch):
    seen = []
    history = [{"role": "assistant", "content": [{"text": "prior@example.test"}]}]
    monkeypatch.setattr(router, "get_model_for", lambda _: "default-model")
    monkeypatch.setattr(router, "get_fallback_for", lambda _: None)
    monkeypatch.setattr(bedrock, "converse", lambda **kwargs: seen.append(kwargs) or "ok")
    router.answer(system="name: Teacher", user_text="raw@example.test", history=history)
    assert seen[0] == {
        "model_id": "default-model", "system": "name: Teacher",
        "messages": history + [{"role": "user", "content": [{"text": "raw@example.test"}]}],
        "max_tokens": 2048, "fallback_model_id": None,
    }
    monkeypatch.setattr(bedrock, "embed", lambda text, **kwargs: seen.append((text, kwargs)) or [1])
    monkeypatch.setattr(db, "rpc", lambda *args, **kwargs: seen.append((args, kwargs)) or [])
    rag.retrieve(institution_id="i", course_id="c", query="raw@example.test")
    assert seen[1] == ("raw@example.test", {"input_type": "search_query"})
    assert seen[2][1] == {}  # no opt-in budget keyword on old DB path


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_AI_REQ_001_embedding_failure_logs_never_echo_provider_body(monkeypatch, caplog, provider):
    marker = "private.student@example.test"
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        openai_embed_model="fake-embed", openrouter_embed_model="fake-embed",
    ))

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            return httpx.Response(503, text=marker, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(bedrock, f"_{provider}_client", lambda **kwargs: Client())
    with pytest.raises(ModelUnavailableError):
        getattr(bedrock, f"_{provider}_embed")("[email]", input_type="search_query", budget=RequestBudget())
    assert marker not in caplog.text
    assert "tutor_provider_error" in caplog.text


def test_AI_REQ_001_chat_failure_logs_never_echo_provider_body(monkeypatch, caplog):
    marker = "private.student@example.test"
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace())

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            return httpx.Response(503, text=marker, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda **kwargs: Client())
    with pytest.raises(ModelUnavailableError):
        bedrock._openrouter_converse(model_id="fake", system="s", messages=[], max_tokens=2048, budget=RequestBudget())
    assert marker not in caplog.text
    assert "tutor_provider_error" in caplog.text


def test_TUTOR_REQ_001_expired_budget_cannot_start_later_rag_rpc(monkeypatch):
    budget = RequestBudget()

    def embed(*args, **kwargs):
        budget.closed = True  # elapsed guard has already returned to caller
        return [0.1]

    monkeypatch.setattr(bedrock, "embed", embed)
    monkeypatch.setattr(db, "get_settings", lambda: SimpleNamespace(
        supabase_url="https://db.example.test", supabase_service_key="fake",
    ))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: pytest.fail("must not create another client"))
    with pytest.raises(TutorTimeout):
        rag.retrieve(institution_id="i", course_id="c", query="q", budget=budget)


def test_AI_REQ_001_opt_in_router_sanitizes_every_text_part_without_mutation(monkeypatch):
    import copy

    history = [{"role": "assistant", "content": [
        {"text": "first@example.test"}, {"text": "name: Example Person"},
    ]}]
    original = copy.deepcopy(history)
    seen = []
    monkeypatch.setattr(router, "get_model_for", lambda _: "chat")
    monkeypatch.setattr(router, "get_fallback_for", lambda _: None)
    monkeypatch.setattr(bedrock, "converse", lambda **kwargs: seen.append(kwargs) or "answer")
    router.answer(system="system@example.test", user_text="current@example.test", history=history,
                  task="chat", budget=RequestBudget())
    outbound = seen[0]
    assert outbound["system"] == "[email]"
    assert outbound["messages"] == [
        {"role": "assistant", "content": [{"text": "[email]"}, {"text": "[name]"}]},
        {"role": "user", "content": [{"text": "[email]"}]},
    ]
    assert history == original
