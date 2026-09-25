import httpx
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic, item_generation_jobs, practice

_COURSE = "00000000-0000-4000-8000-000000000001"
_SKILL = "00000000-0000-4000-8000-000000000010"
_SKILL_2 = "00000000-0000-4000-8000-000000000011"
_SET = "00000000-0000-4000-8000-000000000020"
_INSTITUTION = "00000000-0000-4000-8000-000000000050"


def authenticated_user() -> CurrentUser:
    return CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id=_INSTITUTION,
        app_role="student",
    )


def test_diagnostic_enqueue_race_returns_winner_and_keeps_tenant_filters(monkeypatch):
    calls = []
    winner = {
        "id": "job-1", "institution_id": _INSTITUTION, "course_id": _COURSE,
        "skill_id": _SKILL, "kind": "diagnostic", "status": "pending",
    }

    def select(table, params):
        calls.append((table, params))
        return [] if len(calls) == 1 else [winner]

    def insert(*args, **kwargs):
        response = httpx.Response(409, request=httpx.Request("POST", "https://db"))
        raise httpx.HTTPStatusError("duplicate", request=response.request, response=response)

    monkeypatch.setattr(item_generation_jobs.db, "select", select)
    monkeypatch.setattr(item_generation_jobs.db, "insert", insert)

    row, created = item_generation_jobs.enqueue_diagnostic(
        institution_id=_INSTITUTION, course_id=_COURSE, skill_id=_SKILL,
    )

    assert row == winner
    assert created is False
    for _, params in calls:
        assert params["institution_id"] == f"eq.{_INSTITUTION}"
        assert params["course_id"] == f"eq.{_COURSE}"
        assert params["skill_id"] == f"eq.{_SKILL}"
        assert params["kind"] == "eq.diagnostic"


def test_diagnostic_partial_terminal_failure_stays_ready(monkeypatch):
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "skills":
            return [
                {"id": _SKILL, "name": "Recursion", "bloom_level": "apply"},
                {"id": _SKILL_2, "name": "Iteration", "bloom_level": "apply"},
            ]
        if table == "generated_items":
            return [{
                "id": "item-1", "skill_id": _SKILL, "bloom_level": "apply",
                "prompt": "What is recursion?", "choices": [],
            }]
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic, "enqueue_diagnostic", lambda **kwargs: (
        ({"id": "job-2", "status": "failed"}, False)
        if kwargs["skill_id"] == _SKILL_2 else
        ({"id": "job-1", "status": "pending"}, False)
    ))

    try:
        with TestClient(app) as client:
            response = client.get(f"/courses/{_COURSE}/diagnostic")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["status"] == "ready"
    assert body["readyCount"] == 1
    assert body["failedSkillIds"] == [_SKILL_2]


def test_practice_enqueue_race_reads_existing_offsets_with_tenant_scope(monkeypatch):
    captured = []
    existing = [
        {"id": "job-0", "status": "pending", "context_offset": 0},
        {"id": "job-1", "status": "complete", "context_offset": 1},
    ]

    def select(table, params):
        captured.append((table, params))
        return existing

    def insert(*args, **kwargs):
        response = httpx.Response(409, request=httpx.Request("POST", "https://db"))
        raise httpx.HTTPStatusError("duplicate", request=response.request, response=response)

    monkeypatch.setattr(item_generation_jobs.db, "select", select)
    monkeypatch.setattr(item_generation_jobs.db, "insert", insert)

    rows = item_generation_jobs.enqueue_practice(
        institution_id=_INSTITUTION, course_id=_COURSE, skill_id=_SKILL,
        set_id=_SET, size=2,
    )

    assert rows == existing
    params = captured[0][1]
    assert params["institution_id"] == f"eq.{_INSTITUTION}"
    assert params["course_id"] == f"eq.{_COURSE}"
    assert params["set_id"] == f"eq.{_SET}"
    assert params["kind"] == "eq.practice"


def test_lesson_enqueue_race_reads_existing_step_with_tenant_scope(monkeypatch):
    calls = []
    winner = {
        "id": "job-lesson", "institution_id": _INSTITUTION,
        "course_id": _COURSE, "skill_id": _SKILL, "kind": "lesson",
        "lesson_step_id": "step-1", "status": "pending",
    }

    def select(table, params):
        calls.append((table, params))
        return [] if len(calls) == 1 else [winner]

    def insert(*args, **kwargs):
        response = httpx.Response(409, request=httpx.Request("POST", "https://db"))
        raise httpx.HTTPStatusError("duplicate", request=response.request, response=response)

    monkeypatch.setattr(item_generation_jobs.db, "select", select)
    monkeypatch.setattr(item_generation_jobs.db, "insert", insert)

    row, created = item_generation_jobs.enqueue_lesson(
        institution_id=_INSTITUTION, course_id=_COURSE,
        skill_id=_SKILL, lesson_step_id="step-1",
    )

    assert row == winner
    assert created is False
    for _, params in calls:
        assert params["institution_id"] == f"eq.{_INSTITUTION}"
        assert params["lesson_step_id"] == "eq.step-1"
        assert params["kind"] == "eq.lesson"


def test_new_practice_set_does_not_return_a_dead_zero_queue_set(monkeypatch, caplog):
    app.dependency_overrides[get_current_user] = authenticated_user
    deleted = []
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": _SKILL, "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows: [{"id": _SET, **rows[0]}],
    )
    monkeypatch.setattr(practice, "enqueue_practice", lambda **kwargs: [])
    monkeypatch.setattr(
        practice.db, "delete",
        lambda table, filters: deleted.append((table, filters)) or [],
    )

    try:
        with TestClient(app) as client:
            response = client.post(f"/practice/{_COURSE}/set?size=2")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert deleted == [("quiz_sets", {"id": f"eq.{_SET}"})]
    assert any("dead set" in record.getMessage() for record in caplog.records)


def test_practice_set_detail_reports_generating_with_ready_items(monkeypatch):
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.db, "select", lambda table, params: (
        [{"id": _SET, "skill_id": _SKILL, "kind": "practice", "size": 3,
          "created_at": "2026-09-25T00:00:00Z"}]
        if table == "quiz_sets" else
        [{"id": "item-1", "skill_id": _SKILL, "prompt": "Q", "choices": [],
          "bloom_level": "apply"}]
        if table == "generated_items" else []
    ))
    monkeypatch.setattr(practice, "practice_jobs", lambda **kwargs: [
        {"status": "complete", "context_offset": 0},
        {"status": "in_progress", "context_offset": 1},
        {"status": "pending", "context_offset": 2},
    ])

    try:
        with TestClient(app) as client:
            response = client.get(f"/practice/{_COURSE}/sets/{_SET}")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["status"] == "generating"
    assert body["requestedSize"] == 3
    assert body["readyCount"] == 1
    assert body["pendingCount"] == 2
    assert body["failedCount"] == 0
    assert "correct_choice_id" not in body["items"][0]


def test_practice_set_detail_partial_failure_is_ready_and_playable(monkeypatch):
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.db, "select", lambda table, params: (
        [{"id": _SET, "skill_id": _SKILL, "kind": "practice", "size": 3,
          "created_at": "2026-09-25T00:00:00Z"}]
        if table == "quiz_sets" else
        [{"id": "item-1", "skill_id": _SKILL, "prompt": "Q", "choices": [],
          "bloom_level": "apply"}]
        if table == "generated_items" else []
    ))
    monkeypatch.setattr(practice, "practice_jobs", lambda **kwargs: [
        {"status": "complete", "context_offset": 0},
        {"status": "failed", "context_offset": 1},
        {"status": "failed", "context_offset": 2},
    ])

    try:
        with TestClient(app) as client:
            response = client.get(f"/practice/{_COURSE}/sets/{_SET}")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["status"] == "ready"
    assert body["readyCount"] == 1
    assert body["pendingCount"] == 0
    assert body["failedCount"] == 2
    assert body["failedOffsets"] == [1, 2]
