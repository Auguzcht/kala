from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import dashboard


def instructor_user() -> CurrentUser:
    return CurrentUser(user_id="inst-1", institution_id="institution-1", app_role="instructor")


def test_heatmap_requires_instructor(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="stu-1", institution_id="institution-1", app_role="student")
    try:
        with TestClient(app) as client:
            response = client.get("/dashboard/course-1/heatmap")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_heatmap_builds_student_by_skill_cells(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = instructor_user
    skills = [{"id": "skill-1", "name": "Entropy", "bloom_level": "understand"}]
    enrollments = [{"user_id": "stu-1"}, {"user_id": "stu-2"}]
    users = [{"id": "stu-1", "pseudonym": "Mica V."}, {"id": "stu-2", "pseudonym": "Raf C."}]
    mastery = [
        {"user_id": "stu-1", "skill_id": "skill-1", "estimate": 0.5, "attempts": 4},
        {"user_id": "stu-2", "skill_id": "skill-1", "estimate": 0.2, "attempts": 2},
    ]

    def fake_select(table: str, params: dict[str, str]) -> list[dict]:
        if table == "skills":
            return skills
        if table == "enrollments":
            return enrollments
        if table == "users":
            return users
        return mastery

    monkeypatch.setattr(dashboard.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/dashboard/course-1/heatmap")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["cohortReadiness"] == 0.35
    assert body["skills"][0]["cohortBand"] == "developing"
    assert len(body["cells"]) == 2
    assert body["cells"][0]["band"] == "proficient"
    assert body["students"][0]["pseudonym"] == "Mica V."


def test_at_risk_flags_inactive_student_with_supportive_reason(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = instructor_user
    skills = [{"id": "skill-1", "name": "Entropy", "bloom_level": "understand"}]
    enrollments = [{"user_id": "stu-1"}, {"user_id": "stu-2"}]
    users = [{"id": "stu-1", "pseudonym": "Mica V."}, {"id": "stu-2", "pseudonym": "Raf C."}]
    mastery = [{"user_id": "stu-1", "skill_id": "skill-1", "estimate": 0.2, "attempts": 2}]
    evidence = [
        {"user_id": "stu-1", "skill_id": "skill-1", "type": "practice",
         "correct": True, "created_at": "2025-08-10T00:00:00Z"},
    ]

    def fake_select(table: str, params: dict[str, str]) -> list[dict]:
        if table == "skills":
            return skills
        if table == "enrollments":
            return enrollments
        if table == "users":
            return users
        if table == "mastery_state":
            return mastery
        return evidence

    monkeypatch.setattr(dashboard.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/dashboard/course-1/at-risk")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    flags = response.json()["flags"]
    # stu-2 has no evidence (flagged), stu-1 is inactive but evidenced.
    assert len(flags) == 2
    assert flags[0]["pseudonym"] == "Mica V."
    assert "No activity in" in flags[0]["reason"]


def test_at_risk_good_news_empty_state(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = instructor_user
    monkeypatch.setattr(
        dashboard.db, "select",
        lambda table, params: [] if table in ("skills", "enrollments") else [],
    )

    try:
        with TestClient(app) as client:
            response = client.get("/dashboard/course-1/at-risk")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["flags"] == []


def test_student_twin_drill_down(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = instructor_user
    monkeypatch.setattr(
        dashboard.db, "select",
        lambda table, params: [{"pseudonym": "Mica V."}] if table == "users" else [],
    )
    monkeypatch.setattr(
        dashboard.summary, "twin_payload",
        lambda **kwargs: {"courseId": "course-1", "readiness": 0.3, "skills": [], "evidence": []},
    )

    try:
        with TestClient(app) as client:
            response = client.get("/dashboard/course-1/students/stu-1/twin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["pseudonym"] == "Mica V."
    assert response.json()["readiness"] == 0.3
