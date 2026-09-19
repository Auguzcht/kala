"""Route-level tests for POST /lessons/{course_id}/steps/{step_id}/check,
covering the tenancy fix: a step/check pair that does not actually belong to
the path's course must 404, never write evidence or move mastery."""
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import lessons as lessons_router


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="00000000-0000-4000-8000-000000000040", institution_id="inst-1", app_role="student")


def test_check_belonging_to_a_different_course_is_rejected(monkeypatch) -> None:
    """The step exists and its check_item_id matches, but its lesson belongs
    to a different course than the URL — must 404, and must never reach
    grading (no evidence written, tracer never called)."""
    app.dependency_overrides[get_current_user] = authenticated_user
    graded_calls = []
    evidence_calls = []

    def fake_select(table, params):
        if table == "guided_lesson_steps":
            return [{"id": "00000000-0000-4000-8000-000000000070", "lesson_id": "lesson-in-course-a",
                     "check_item_id": "00000000-0000-4000-8000-0000000000c1"}]
        if table == "guided_lessons":
            # Ownership check filters by course_id=eq.course-b (the URL) but
            # the lesson actually lives in course-a -> no match.
            return []
        return []

    monkeypatch.setattr(lessons_router.db, "select", fake_select)
    monkeypatch.setattr(lessons_router.item_gen, "grade",
                        lambda **kw: graded_calls.append(kw) or {
                            "skillId": "s-1", "courseId": "00000000-0000-4000-8000-0000000000a1",
                            "correct": True, "explanation": "x",
                        })
    monkeypatch.setattr(lessons_router.db, "insert_evidence",
                        lambda rows: evidence_calls.extend(rows))

    try:
        with TestClient(app) as client:
            response = client.post(
                "/lessons/course-b/steps/00000000-0000-4000-8000-000000000070/check",
                json={"item_id": "00000000-0000-4000-8000-0000000000c1", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert graded_calls == []      # never reached grading
    assert evidence_calls == []    # never wrote evidence against course-b


def test_check_belonging_to_this_course_is_accepted(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_calls = []

    def fake_select(table, params):
        if table == "guided_lesson_steps":
            return [{"id": "00000000-0000-4000-8000-000000000070", "lesson_id": "lesson-1", "check_item_id": "00000000-0000-4000-8000-0000000000c1"}]
        if table == "guided_lessons":
            return [{"id": "lesson-1"}]  # owned by course-a + inst-1
        return []

    monkeypatch.setattr(lessons_router.db, "select", fake_select)
    monkeypatch.setattr(lessons_router.item_gen, "grade", lambda **kw: {
        "skillId": "s-1", "courseId": "00000000-0000-4000-8000-0000000000a1", "correct": True, "explanation": "nice",
    })
    monkeypatch.setattr(lessons_router.db, "insert_evidence",
                        lambda rows: evidence_calls.extend(rows) or rows)
    monkeypatch.setattr(lessons_router.tracer, "apply_evidence", lambda **kw: {"estimate": 0.6})
    monkeypatch.setattr(lessons_router.srs, "review", lambda **kw: None)
    monkeypatch.setattr(lessons_router.xp, "summary", lambda **kw: {"xp": 10})

    try:
        with TestClient(app) as client:
            response = client.post(
                "/lessons/00000000-0000-4000-8000-0000000000a1/steps/00000000-0000-4000-8000-000000000070/check",
                json={"item_id": "00000000-0000-4000-8000-0000000000c1", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["advance"] is True
    assert evidence_calls[0]["course_id"] == "00000000-0000-4000-8000-0000000000a1"
    assert evidence_calls[0]["type"] == "tutor"


def test_check_item_mismatch_still_404s(monkeypatch) -> None:
    """No step at all matches the (step_id, item_id) pair — the original
    guard, unchanged by the tenancy fix."""
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(lessons_router.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.post(
                "/lessons/00000000-0000-4000-8000-0000000000a1/steps/00000000-0000-4000-8000-000000000070/check",
                json={"item_id": "wrong-item", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
