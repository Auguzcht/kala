# APPROVAL-01 regression coverage; all providers and persistence are mocked.
import json
import logging
import threading
import time
from functools import partial

import anyio
import httpx
import pytest
from app.ai import bedrock
from app.ai.request_budget import RequestBudget
from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import tutor
from conftest import CONVERSATION_ID, COURSE_ID, INSTITUTION_ID, USER_ID
from fastapi.testclient import TestClient


def test_persisted_tutor_turns_have_matching_bulk_insert_keys(monkeypatch) -> None:
    """The nullable user style still has to be present in a bulk insert.

    PostgREST rejects an array whose objects have different key sets with
    PGRST102, even when the omitted column is nullable.
    """
    inserted = []

    def fake_select(table, _params, **kwargs):
        if table == "tutor_conversations":
            return [{
                "id": "00000000-0000-4000-8000-000000000060",
                "course_id": "00000000-0000-4000-8000-000000000001",
                "skill_id": None,
                "title": None,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }]
        return []

    def fake_insert(table, rows, **kwargs):
        assert table == "tutor_messages"
        assert len({frozenset(row) for row in rows}) == 1
        inserted.extend(rows)
        return rows

    monkeypatch.setattr(tutor.db, "select", fake_select)
    monkeypatch.setattr(tutor.db, "insert", fake_insert)
    monkeypatch.setattr(tutor.db, "update", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.rag, "retrieve", lambda **kwargs: [])
    monkeypatch.setattr(tutor.model_router, "answer", lambda **kwargs: "An answer")

    result = anyio.run(partial(tutor.ask,
        tutor.Ask(
            course_id="00000000-0000-4000-8000-000000000001",
            question="What is recursion?",
            style="detail",
            conversation_id="00000000-0000-4000-8000-000000000060",
        ),
        CurrentUser(
            user_id="00000000-0000-4000-8000-000000000040",
            institution_id="00000000-0000-4000-8000-000000000050",
            app_role="student",
        ),
    ))

    assert result == {
        "answer": "An answer",
        "conversationId": "00000000-0000-4000-8000-000000000060",
    }
    assert inserted[0]["style"] is None
    assert inserted[1]["style"] == "detail"




@pytest.fixture
def tutor_client(monkeypatch):
    user = CurrentUser(user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student")

    def select(table, params, **kwargs):
        if table == "tutor_conversations":
            return [{"id": CONVERSATION_ID, "course_id": COURSE_ID, "title": None}]
        return []

    monkeypatch.setattr(tutor.db, "select", select)
    monkeypatch.setattr(tutor.db, "insert", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.db, "update", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.rag, "retrieve", lambda **kwargs: [])
    monkeypatch.setattr(tutor.model_router, "answer", lambda **kwargs: "An answer")
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def payload(persistent=False):
    return {"course_id": COURSE_ID, "question": "question@example.test", **(
        {"conversation_id": CONVERSATION_ID} if persistent else {}
    )}


def test_AI_REQ_001_question_email_never_reaches_embedding_payload(monkeypatch):
    # Use the real tutor -> RAG -> embed dispatch -> HTTP payload construction.
    from types import SimpleNamespace

    from app.ai import rag

    captured = []
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(
        ai_provider="openrouter", embed_provider="openai", openai_embed_model="fake-model",
    ))

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, path, json):
            captured.append(json)
            return httpx.Response(200, json={"data": [{"embedding": [0.1]}]},
                                  request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(bedrock, "_openai_client", lambda **kwargs: Client())
    monkeypatch.setattr(rag.db, "rpc", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.model_router, "answer", lambda **kwargs: "An answer")
    user = CurrentUser(user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student")
    anyio.run(partial(tutor.ask, tutor.Ask(**payload()), user))
    assert captured[0]["input"] == "[email]"
    assert "question@example.test" not in json.dumps(captured)


def test_AI_REQ_001_history_context_and_question_sanitized_but_storage_unchanged(monkeypatch, caplog):
    from types import SimpleNamespace

    captured = []
    stored = []
    history = [{"role": "user", "content": "prior@example.test name: Prior Person"}]
    original = [dict(m) for m in history]

    def select(table, params, **kwargs):
        if table == "tutor_conversations":
            return [{"id": CONVERSATION_ID, "course_id": COURSE_ID, "title": None}]
        if table == "tutor_messages": return history
        return [{"filename": "notes@example.test", "extracted_text": "name: Note Person"}]

    monkeypatch.setattr(tutor.db, "select", select)
    monkeypatch.setattr(tutor.db, "insert", lambda table, rows, **kwargs: stored.extend(rows))
    monkeypatch.setattr(tutor.db, "update", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.rag, "retrieve", lambda **kwargs: [{"chunk_text": "course@example.test"}])
    monkeypatch.setattr(tutor.model_router, "get_model_for", lambda _: "fake-chat")
    monkeypatch.setattr(tutor.model_router, "get_fallback_for", lambda _: "fake-fallback")
    monkeypatch.setattr(bedrock, "get_settings", lambda: SimpleNamespace(ai_provider="openrouter"))

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, path, json):
            captured.append(json)
            return httpx.Response(200, json={"choices": [{"message": {"content": "Answer"}}]},
                                  request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda **kwargs: Client())
    user = CurrentUser(user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student")
    caplog.set_level(logging.INFO)
    assert anyio.run(partial(tutor.ask, tutor.Ask(**payload(True)), user))["answer"] == "Answer"
    outbound = json.dumps(captured)
    assert all(email not in outbound for email in (
        "prior@example.test", "question@example.test", "course@example.test", "notes@example.test",
    ))
    assert "Prior Person" not in outbound and "Note Person" not in outbound
    assert history == original
    assert stored[0]["content"] == "question@example.test"
    assert not any(value in caplog.text for value in ("question@example.test", "Prior Person", USER_ID))
    timing = [r for r in caplog.records if r.message.startswith("tutor_timing")]
    assert len(timing) == 1
    assert all(key in timing[0].message for key in ("retrieval_ms", "chat_ms", "persistent", "provider_role", "fallback_used", "success"))


def test_TUTOR_REQ_001_slow_chat_returns_503_within_real_26_second_budget(tutor_client, monkeypatch, caplog, record_property):
    release = threading.Event()
    finished = threading.Event()

    def slow(**kwargs):
        try:
            release.wait(28)
            return "too late"
        finally:
            finished.set()

    monkeypatch.setattr(tutor.model_router, "answer", slow)
    started = time.monotonic()
    try:
        response = tutor_client.post("/tutor/ask", json=payload())
        elapsed = time.monotonic() - started
        record_property("handler_response_seconds", elapsed)
        assert response.status_code == 503
        assert response.json() == {
            "detail": "The tutor took too long to respond. Please try again.", "code": "tutor_timeout",
        }
        assert 22 <= elapsed < 26
        assert not finished.is_set()  # response did not wait for the synchronous worker
        assert len([r for r in caplog.records if r.message.startswith("tutor_timing")]) == 1
    finally:
        release.set()
        assert finished.wait(1)


@pytest.mark.parametrize("stage", ["insert", "update"])
def test_TUTOR_REQ_001_persistence_error_preserves_answer_and_safe_warning(tutor_client, monkeypatch, caplog, stage):
    def fail(*args, **kwargs):
        raise RuntimeError("private question@example.test")

    monkeypatch.setattr(tutor.db, stage, fail)
    response = tutor_client.post("/tutor/ask", json=payload(True))
    assert response.status_code == 200 and response.json()["answer"] == "An answer"
    assert "tutor_persistence_failed conversation=00000000 stage=persist_" in caplog.text
    assert "private" not in caplog.text and "question@example.test" not in caplog.text
    assert CONVERSATION_ID not in caplog.text
    assert "persistence_failed" in caplog.text


def test_TUTOR_REQ_001_no_budget_for_persistence_preserves_answer(tutor_client, monkeypatch):
    def answer(**kwargs):
        kwargs["budget"].deadline = time.monotonic() + 2.9
        return "An answer"

    monkeypatch.setattr(tutor.model_router, "answer", answer)
    monkeypatch.setattr(tutor.db, "insert", lambda *a, **k: pytest.fail("no budget for insert"))
    response = tutor_client.post("/tutor/ask", json=payload(True))
    assert response.status_code == 200 and response.json()["answer"] == "An answer"


def test_TUTOR_REQ_001_slow_persistence_preserves_answer_and_cannot_start_update(tutor_client, monkeypatch):
    release = threading.Event()
    finished = threading.Event()
    updates = []

    def short_budget(): return RequestBudget(seconds=0.2, reserve=0.05)
    def insert(*args, **kwargs):
        release.wait(1)
        finished.set()
        return []

    monkeypatch.setattr(tutor, "RequestBudget", short_budget)
    monkeypatch.setattr(tutor.db, "insert", insert)
    monkeypatch.setattr(tutor.db, "update", lambda *a, **k: updates.append(True))
    started = time.monotonic()
    try:
        response = tutor_client.post("/tutor/ask", json=payload(True))
        assert response.status_code == 200 and response.json()["answer"] == "An answer"
        assert time.monotonic() - started < 0.4
    finally:
        release.set()
        assert finished.wait(1)
    assert updates == []


def test_TUTOR_REQ_001_ownership_404_is_preserved(tutor_client, monkeypatch, caplog):
    monkeypatch.setattr(tutor.db, "select", lambda *a, **k: [])
    assert tutor_client.post("/tutor/ask", json=payload(True)).status_code == 404
    assert "'provider_role': 'none'" in caplog.text
