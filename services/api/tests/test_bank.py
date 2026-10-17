import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.bank import kick as kick_module
from app.deps import CurrentUser
from app.routers import bank as bank_router
from fastapi import HTTPException


def test_kick_bank_debounces_second_call(monkeypatch):
    updates = []
    invokes = []
    def update(*args, **kwargs):
        result = [{"id": "c"}] if not updates else []
        updates.append(1)
        return result
    monkeypatch.setattr(kick_module.db, "update", update)
    monkeypatch.setattr(kick_module, "get_settings", lambda: type("S", (), {"worker_function_arn": "arn", "aws_region": "ap-southeast-1"})())
    class Lambda:
        def invoke(self, **kwargs): invokes.append(kwargs)
    monkeypatch.setattr(kick_module.boto3, "client", lambda *args, **kwargs: Lambda())
    assert kick_module.kick_bank("c", "status") is True
    assert kick_module.kick_bank("c", "status") is False
    assert len(invokes) == 1


def test_kick_lesson_checks_invokes_only_the_requested_lesson(monkeypatch):
    invokes = []
    states = {}

    def update(table, filters, values):
        assert table == "worker_state"
        key = filters["key"].removeprefix("eq.")
        state = states.get(key)
        if not state:
            return []
        if state["updated_at"] >= datetime.now(UTC) - timedelta(seconds=60):
            return []
        if state.get("lease_until") and state["lease_until"] > datetime.now(UTC):
            return []
        states[key] = {"updated_at": datetime.now(UTC), "lease_until": None}
        return [{"key": key}]

    def insert(table, rows):
        assert table == "worker_state"
        row = rows[0]
        if row["key"] in states:
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(409, request=request)
            raise httpx.HTTPStatusError("duplicate key", request=request, response=response)
        states[row["key"]] = {"updated_at": datetime.now(UTC), "lease_until": None}
        return [row]

    monkeypatch.setattr(kick_module.db, "update", update)
    monkeypatch.setattr(kick_module.db, "insert", insert)
    monkeypatch.setattr(kick_module, "get_settings", lambda: type("S", (), {"worker_function_arn": "arn", "aws_region": "region"})())
    class Lambda:
        def invoke(self, **kwargs):
            invokes.append(kwargs)
    monkeypatch.setattr(kick_module.boto3, "client", lambda *args, **kwargs: Lambda())
    assert kick_module.kick_lesson_checks("course", "lesson") is True
    assert len(invokes) == 1
    assert json.loads(invokes[0]["Payload"]) == {
        "trigger": "lesson_checks", "courseId": "course", "lessonId": "lesson", "chainDepth": 0,
    }


def test_lesson_check_kicks_debounce_same_lesson_but_not_other_lessons(monkeypatch):
    invokes = []
    states = {}

    def update(table, filters, values):
        key = filters["key"].removeprefix("eq.")
        state = states.get(key)
        if not state or state["updated_at"] >= datetime.now(UTC) - timedelta(seconds=60):
            return []
        if state.get("lease_until") and state["lease_until"] > datetime.now(UTC):
            return []
        states[key] = {"updated_at": datetime.now(UTC), "lease_until": None}
        return [{"key": key}]

    def insert(_table, rows):
        row = rows[0]
        if row["key"] in states:
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(409, request=request)
            raise httpx.HTTPStatusError("duplicate key", request=request, response=response)
        states[row["key"]] = {"updated_at": datetime.now(UTC), "lease_until": None}
        return [row]

    monkeypatch.setattr(kick_module.db, "update", update)
    monkeypatch.setattr(kick_module.db, "insert", insert)
    monkeypatch.setattr(kick_module, "get_settings", lambda: type("S", (), {"worker_function_arn": "arn", "aws_region": "region"})())

    class Lambda:
        def invoke(self, **kwargs):
            invokes.append(kwargs)

    monkeypatch.setattr(kick_module.boto3, "client", lambda *args, **kwargs: Lambda())
    assert kick_module.kick_lesson_checks("course", "lesson-a") is True
    assert kick_module.kick_lesson_checks("course", "lesson-a") is False
    assert kick_module.kick_lesson_checks("course", "lesson-b") is True
    assert len(invokes) == 2


def test_lesson_check_kick_skips_a_live_worker_lease(monkeypatch):
    invokes = []
    states = {"lesson_check_kick:lesson": {
        "updated_at": datetime.now(UTC) - timedelta(seconds=61),
        "lease_until": datetime.now(UTC) + timedelta(seconds=60),
    }}

    monkeypatch.setattr(kick_module.db, "update", lambda table, filters, values: [])
    def insert(*args, **kwargs):
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(409, request=request)
        raise httpx.HTTPStatusError("duplicate key", request=request, response=response)
    monkeypatch.setattr(kick_module.db, "insert", insert)
    monkeypatch.setattr(kick_module, "get_settings", lambda: type("S", (), {"worker_function_arn": "arn", "aws_region": "region"})())

    class Lambda:
        def invoke(self, **kwargs):
            invokes.append(kwargs)

    monkeypatch.setattr(kick_module.boto3, "client", lambda *args, **kwargs: Lambda())
    assert kick_module.kick_lesson_checks("course", "lesson") is False
    assert not invokes


def test_student_status_hides_last_error_and_other_course_is_404(monkeypatch):
    user = CurrentUser("u", "i", "student")
    def select(table, params):
        if table == "courses": return [{"id": "c", "institution_id": "i"}]
        if table == "enrollments": return [{"user_id": "u"}]
        if table == "skills": return [{"id": "s"}, {"id": "missing"}]
        if table == "skill_bank_state": return [{"skill_id": "s", "status": "error", "mcq_ready": 0,
            "mcq_target": 5, "depth": 2, "last_error": "secret"}]
        return []
    monkeypatch.setattr(bank_router.db, "select", select)
    monkeypatch.setattr(bank_router, "kick_bank", lambda *args: False)
    result = bank_router.bank_status("c", user)
    assert "lastError" not in result["skills"][0]
    assert result["skills"][0]["usable"] is False
    missing = result["skills"][1]
    assert missing == {"skillId": "missing", "status": "waiting_content", "mcqReady": 0,
                       "mcqTarget": 0, "depth": 0, "usable": False}
    assert result["building"] is True

    def other_course(table, params):
        if table == "courses":
            return [{"id": "c", "institution_id": "i"}]
        return []
    monkeypatch.setattr(bank_router.db, "select", other_course)
    with pytest.raises(HTTPException) as exc:
        bank_router.bank_status("c", user)
    assert exc.value.status_code == 404
