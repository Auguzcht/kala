"""AUTH-REQ-007: real Bank admission, synthetic business boundaries only."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import (
    bank,
    courses,
    diagnostic,
    flashcards,
    gamification,
    lessons,
    practice,
    twin,
)

C = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
I = "00000000-0000-4000-8000-000000000050"
U = "00000000-0000-4000-8000-000000000040"
SK = "00000000-0000-4000-8000-000000000010"
SET = "00000000-0000-4000-8000-000000000020"
CON = "00000000-0000-4000-8000-000000000060"
STAMP = "2026-10-25T00:00:00Z"
ROUTES = [
    f"/courses/{C}", f"/courses/{C}/memory/summary",
    f"/courses/{C}/twin", f"/courses/{C}/next-up", f"/courses/{C}/plan",
    f"/courses/{C}/content", f"/courses/{C}/modules",
    f"/courses/{C}/diagnostic/status", f"/courses/{C}/diagnostic",
    f"/flashcards/{C}/skills/{SK}/cards", f"/flashcards/{C}/deck",
    f"/gamification/{C}/summary", f"/practice/{C}/next", f"/practice/{C}/sets",
    f"/practice/{C}/sets/{SET}", f"/practice/{C}/sets/{SET}/results",
    f"/lessons/{C}/skill/{SK}", f"/tutor/conversations?course_id={C}",
    f"/tutor/conversations/{CON}",
]


@pytest.fixture
def boundary(monkeypatch):
    user = CurrentUser(U, I, "student", course_id=OTHER)
    state = {"enrolled": True, "course_exists": True}
    admission, protected = [], []

    def select(table, params, **kwargs):
        if table == "courses":
            admission.append((table, params))
            assert params["id"] == f"eq.{C}"
            assert params["institution_id"] == f"eq.{user.institution_id}"
            return [{"id": C, "institution_id": I, "bank_serving": False,
                     "lms_course_id": "synthetic", "title": "Synthetic"}] if state["course_exists"] and user.institution_id == I else []
        if table == "enrollments":
            admission.append((table, params))
            assert params["course_id"] == f"eq.{C}"
            assert params["user_id"] == f"eq.{U}"
            if params.get("role") == "eq.instructor":
                return [{"course_id": C}]
            assert params == {"course_id": f"eq.{C}", "user_id": f"eq.{U}", "select": "user_id", "limit": "1"}
            return [{"user_id": U}] if state["enrolled"] else []
        if table == "tutor_conversations" and "id" in params:
            admission.append(("owned-conversation", params))
            assert params["id"] == f"eq.{CON}"
            assert params["user_id"] == f"eq.{U}"
            assert params["institution_id"] == f"eq.{user.institution_id}"
            return [{"id": CON, "course_id": C, "skill_id": None, "title": None,
                     "created_at": STAMP, "updated_at": STAMP}]
        protected.append(("select", table))
        if table == "skills" and params.get("limit") == "1":
            return [{"id": SK, "name": "Synthetic", "bloom_level": "apply", "module_ref": None}]
        if table == "quiz_sets":
            return [{"id": SET, "skill_id": SK, "kind": "practice", "size": 0, "created_at": STAMP}]
        return []

    def operation(label, result):
        def run(*args, **kwargs):
            protected.append((label, args))
            return result
        return run

    monkeypatch.setattr(bank.db, "select", select)
    for name in ("insert", "insert_evidence", "update", "upsert", "delete", "rpc"):
        monkeypatch.setattr(bank.db, name, operation(name, []))
    gate = Mock(wraps=bank._course_for_user)
    monkeypatch.setattr(bank, "_course_for_user", gate)
    monkeypatch.setattr(twin.summary, "twin_payload", operation("twin", {"skills": [], "evidence": []}))
    monkeypatch.setattr(twin.item_gen, "weakest_skill", operation("next-up", None))
    monkeypatch.setattr(courses.srs, "new_remaining_today", operation("memory", 0))
    monkeypatch.setattr(diagnostic, "_diagnostic_availability", operation("availability", {
        "items": [], "pendingSkillIds": [], "failedSkillIds": [], "waitingForMaterialCount": 0,
    }))
    monkeypatch.setattr(diagnostic, "enqueue_diagnostic", operation("queue", ({}, True)))
    monkeypatch.setattr(diagnostic, "kick_bank", operation("kick", None))
    monkeypatch.setattr(flashcards, "_skill_map", operation("study-skills", {}))
    monkeypatch.setattr(flashcards.srs, "stats", operation("study-stats", {}))
    monkeypatch.setattr(flashcards, "record_exposure", operation("study-exposure", None))
    monkeypatch.setattr(gamification.xp, "summary", operation("xp", {}))
    monkeypatch.setattr(practice, "_resolve_skill", operation("test-skill", None))
    monkeypatch.setattr(practice, "_attempts_by_set", operation("attempts", {}))
    monkeypatch.setattr(practice, "practice_jobs", operation("jobs", []))
    monkeypatch.setattr(practice, "record_set_exposures", operation("set-exposures", 0))
    monkeypatch.setattr(lessons.lessons, "get_or_generate_lesson", operation("lesson-generation", {"status": "ready"}))
    connector = Mock()
    connector.get_content.side_effect = operation("lms-content", ([], {}))
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_lms_connector] = lambda: connector
    try:
        with TestClient(app) as client:
            yield client, user, state, admission, protected, gate
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("actor", ["enrolled", "non-enrolled", "foreign", "missing-course", "instructor", "admin"])
def test_student_read_admission_and_staff_regression(boundary, route, actor):
    client, user, state, admission, protected, gate = boundary
    if actor == "non-enrolled":
        state["enrolled"] = False
    if actor == "foreign":
        user.institution_id = OTHER
    if actor == "missing-course":
        state["course_exists"] = False
    if actor in {"instructor", "admin"}:
        user.app_role = actor
    response = client.get(route)
    denied = actor in {"non-enrolled", "foreign", "missing-course"}
    assert response.status_code == (404 if denied else 200), response.text
    if actor in {"instructor", "admin"}:
        gate.assert_not_called()
    else:
        gate.assert_called_once_with(C, user)
    if denied:
        assert response.json() == {"detail": "course not found"}
        assert protected == [], "no protected read/generation/claim/exposure/worker operation after denial"
        expected = ["courses", "enrollments"] if actor == "non-enrolled" else ["courses"]
        if route.endswith(CON):
            expected.insert(0, "owned-conversation")
        assert [table for table, _ in admission] == expected


@pytest.mark.parametrize("order", [("diagnostic", "bank"), ("bank", "diagnostic")])
def test_bank_diagnostic_import_orders_under_shared_isolation(order):
    code = "import runpy; runpy.run_path('../conftest.py'); " + "; ".join(
        f"import app.routers.{name}" for name in order)
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
