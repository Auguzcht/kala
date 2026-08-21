from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import diagnostic


class FakeConnector:
    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None:
        assert (course_ref, column_id, user_ref, score) == ("_4_1", "_8_1", "_6_1", 85.0)

    def get_roster(self, course_ref: str) -> list[dict]:
        return [{"lms_user_id": "user-1", "role": "Student"}]

    def get_content(self, course_ref: str) -> list[dict]:
        return [{"lms_content_id": "content-1", "title": "Lesson"}]

    def get_assessments(self, course_ref: str) -> list[dict]:
        return [{"lms_column_id": "column-1", "name": "Quiz"}]


def authenticated_user() -> CurrentUser:
    return CurrentUser(
        user_id="user-1",
        institution_id="institution-1",
        app_role="student",
    )


def fake_course_select(table: str, params: dict[str, str]) -> list[dict]:
    assert table == "courses"
    assert params["institution_id"] == "eq.institution-1"
    assert params["id"] == "eq.course-1"
    return [{"lms_course_id": "_4_1"}]


def test_course_data_routes_require_lti_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/courses/course-1/content")

    assert response.status_code == 401
    assert response.json() == {"detail": "missing bearer token"}


def test_course_data_routes_are_authenticated_and_tenant_scoped(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[get_lms_connector] = FakeConnector
    monkeypatch.setattr(diagnostic.db, "select", fake_course_select)

    try:
        with TestClient(app) as client:
            content = client.get("/courses/course-1/content")
            assessments = client.get("/courses/course-1/assessments")
            roster = client.get("/courses/course-1/roster")
            grade = client.patch(
                "/courses/course-1/assessments/_8_1/grade",
                json={"user_id": "_6_1", "score": 85},
            )
    finally:
        app.dependency_overrides.clear()

    assert content.status_code == 200
    assert content.json() == [{"lms_content_id": "content-1", "title": "Lesson"}]
    assert assessments.status_code == 200
    assert assessments.json() == [{"lms_column_id": "column-1", "name": "Quiz"}]
    assert roster.status_code == 200
    assert roster.json() == [{"lms_user_id": "user-1", "role": "Student"}]
    assert grade.status_code == 200
    assert grade.json() == {
        "courseId": "course-1",
        "columnId": "_8_1",
        "userId": "_6_1",
        "score": 85.0,
    }