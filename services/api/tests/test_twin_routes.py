from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import courses, twin


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="user-1", institution_id="institution-1", app_role="student")


def test_course_meta_returns_title(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        courses.db, "select",
        lambda table, params: [{"id": "course-1", "title": "Thermodynamics I", "lms_course_id": "ME301"}],
    )

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "course-1", "title": "Thermodynamics I", "lmsCourseId": "ME301"}


def test_course_meta_404s_outside_the_institution(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(courses.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/courses/foreign-course")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_twin_returns_skills_bands_and_evidence(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    skills = [
        {"id": "skill-1", "name": "Cycle Analysis", "bloom_level": "apply"},
        {"id": "skill-2", "name": "Entropy", "bloom_level": "understand"},
    ]
    mastery = [{"skill_id": "skill-1", "estimate": 0.5, "attempts": 3}]
    events = [
        {"id": "ev-1", "skill_id": "skill-1", "type": "practice", "correct": True,
         "latency_ms": 1200, "created_at": "2025-08-25T00:00:00Z"},
    ]

    def fake_select(table: str, params: dict[str, str]) -> list[dict]:
        if table == "skills":
            return skills
        if table == "mastery_state":
            return mastery
        return events

    monkeypatch.setattr(twin.db, "select", fake_select)
    monkeypatch.setattr(twin.readiness, "compute", lambda **kwargs: 0.5)

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/twin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["readiness"] == 0.5
    assert len(body["skills"]) == 2
    assert body["skills"][0]["band"] == "proficient"   # 0.5
    assert body["skills"][1]["band"] == "no-evidence"  # no mastery row
    assert body["skills"][1]["estimate"] is None
    assert body["evidence"][0]["skillName"] == "Cycle Analysis"


def test_twin_empty_when_course_has_no_skills(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(twin.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/twin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "course-1", "readiness": None, "skills": [], "evidence": []}


def test_next_up_picks_weakest_skill_with_reason(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        twin.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Cycle Analysis", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        twin.db, "select",
        lambda table, params: [{"skill_id": "skill-1", "estimate": 0.3}],
    )

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/next-up")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    next_up = response.json()["next"]
    assert next_up["skillName"] == "Cycle Analysis"
    assert next_up["estimate"] == 0.3
    assert "lowest mastery" in next_up["reason"]


def test_next_up_none_when_course_has_no_skills(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(twin.item_gen, "weakest_skill", lambda **kwargs: None)

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/next-up")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "course-1", "next": None}
