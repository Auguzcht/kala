from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import diagnostic
from wi26_student_fixtures import enrolled_student_reads


class FakeConnector:
    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None:
        assert (course_ref, column_id, user_ref, score) == ("_4_1", "_8_1", "_6_1", 85.0)

    def get_roster(self, course_ref: str) -> list[dict]:
        return [{"lms_user_id": "00000000-0000-4000-8000-000000000040", "role": "Student"}]

    def get_content(self, course_ref: str, *, include_attachments: bool = False, max_attachments: int = 3):
        return [{"lms_content_id": "content-1", "title": "Lesson"}], {"fetched": 0, "skipped_unsupported": 0, "failed": 0, "capped": 0, "remaining": 0, "chunks": 0}

    def get_assessments(self, course_ref: str) -> list[dict]:
        return [{"lms_column_id": "column-1", "name": "Quiz"}]


def authenticated_user() -> CurrentUser:
    return CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id="institution-1",
        app_role="student",
    )


def fake_course_select(table: str, params: dict[str, str]) -> list[dict]:
    assert table == "courses"
    assert params["institution_id"] == "eq.institution-1"
    assert params["id"] == "eq.00000000-0000-4000-8000-000000000001"
    return [{"lms_course_id": "_4_1"}]


def test_course_data_routes_require_lti_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/courses/00000000-0000-4000-8000-000000000001/content")

    assert response.status_code == 401
    assert response.json() == {"detail": "missing bearer token"}


def test_INGEST_REQ_001_course_data_routes_are_authenticated_and_tenant_scoped(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[get_lms_connector] = FakeConnector
    monkeypatch.setattr(diagnostic.db, "select", enrolled_student_reads(fake_course_select))

    try:
        with TestClient(app) as client:
            content = client.get("/courses/00000000-0000-4000-8000-000000000001/content")
            assessments = client.get("/courses/00000000-0000-4000-8000-000000000001/assessments")
            roster = client.get("/courses/00000000-0000-4000-8000-000000000001/roster")
            grade = client.patch(
                "/courses/00000000-0000-4000-8000-000000000001/assessments/_8_1/grade",
                json={"user_id": "_6_1", "score": 85},
            )
    finally:
        app.dependency_overrides.clear()

    assert content.status_code == 200
    assert content.json() == [{"lms_content_id": "content-1", "title": "Lesson"}]
    assert assessments.status_code == 403
    assert assessments.json() == {"detail": "insufficient role"}
    assert roster.status_code == 403
    assert roster.json() == {"detail": "insufficient role"}
    assert grade.status_code == 403
    assert grade.json() == {"detail": "insufficient role"}
