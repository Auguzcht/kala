"""INGEST-REQ-001: gradebook routes reuse the upload staff/course gate.

All database reads and LMS operations are mocked. These requests exercise the
real role dependency and course gate through FastAPI without external calls.
"""
from unittest.mock import Mock

import pytest
from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.lms.blackboard import BlackboardConnector
from app.main import app
from app.routers import diagnostic
from conftest import (
    COLUMN_ID,
    COURSE_ID,
    COURSE_ID_2,
    INSTITUTION_ID,
    USER_ID,
    USER_ID_2,
)
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(params=["GET", "PATCH"], ids=["assessments", "grade"])
def gradebook_request(request):
    def send(client):
        if request.param == "GET":
            return client.get(f"/courses/{COURSE_ID}/assessments")
        return client.patch(
            f"/courses/{COURSE_ID}/assessments/{COLUMN_ID}/grade",
            json={"user_id": USER_ID_2, "score": 85.0},
        )

    return send


@pytest.fixture
def boundary(monkeypatch):
    user = CurrentUser(
        user_id=USER_ID, institution_id=INSTITUTION_ID,
        app_role="instructor", course_id=COURSE_ID,
    )
    enrollments = []
    reads = []
    courses = [{"lms_course_id": "_course_1"}]

    def select(table, params):
        reads.append((table, params))
        if table == "enrollments":
            assert params == {
                "institution_id": f"eq.{INSTITUTION_ID}",
                "user_id": f"eq.{USER_ID}",
                "course_id": f"eq.{COURSE_ID}",
                "role": "eq.instructor",
                "select": "course_id", "limit": "1",
            }
            return [
                row for row in enrollments
                if all(params[key] == f"eq.{row[key]}" for key in (
                    "institution_id", "user_id", "course_id", "role",
                ))
            ]
        assert table == "courses"
        assert params == {
            "id": f"eq.{COURSE_ID}",
            "institution_id": f"eq.{INSTITUTION_ID}",
            "select": "lms_course_id", "limit": "1",
        }
        return courses

    monkeypatch.setattr(diagnostic.db, "select", select)
    gate = Mock(wraps=diagnostic._assert_teaches_course)
    monkeypatch.setattr(diagnostic, "_assert_teaches_course", gate)
    connector = Mock(spec=BlackboardConnector)
    connector.get_assessments.return_value = [{"id": COLUMN_ID, "name": "Quiz"}]
    overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_lms_connector] = lambda: connector
    try:
        with TestClient(app) as client:
            yield client, user, enrollments, reads, connector, gate, courses
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)


def _enrollment(**overrides):
    return {
        "institution_id": INSTITUTION_ID, "user_id": USER_ID,
        "course_id": COURSE_ID, "role": "instructor", **overrides,
    }


def test_INGEST_REQ_001_student_gets_403(boundary, gradebook_request):
    client, user, enrollments, reads, connector, gate, _ = boundary
    user.app_role = "student"
    enrollments.append(_enrollment())

    response = gradebook_request(client)

    assert response.status_code == 403
    assert response.json() == {"detail": "insufficient role"}
    assert reads == []
    gate.assert_not_called()
    assert connector.mock_calls == []


@pytest.mark.parametrize("enrollment", [
    _enrollment(course_id=COURSE_ID_2),
    _enrollment(institution_id="another-institution"),
    _enrollment(role="student"),
    _enrollment(user_id=USER_ID_2),
], ids=["other-course", "other-institution", "student-enrollment", "other-user"])
def test_INGEST_REQ_001_unauthorized_instructor_gets_404(
    boundary, gradebook_request, enrollment,
):
    client, user, enrollments, reads, connector, gate, _ = boundary
    enrollments.append(enrollment)

    response = gradebook_request(client)

    assert response.status_code == 404
    assert response.json() == {"detail": "course not found"}
    gate.assert_called_once_with(user=user, course_id=COURSE_ID)
    assert [table for table, _ in reads] == ["enrollments"]
    assert connector.mock_calls == []


def test_INGEST_REQ_001_course_instructor_reaches_lms(boundary, gradebook_request):
    client, user, enrollments, reads, connector, gate, _ = boundary
    enrollments.append(_enrollment())

    response = gradebook_request(client)

    assert response.status_code == 200
    gate.assert_called_once_with(user=user, course_id=COURSE_ID)
    assert [table for table, _ in reads] == ["enrollments", "courses"]
    if response.request.method == "GET":
        assert response.json() == [{"id": COLUMN_ID, "name": "Quiz"}]
        connector.get_assessments.assert_called_once_with("_course_1")
        connector.post_grade.assert_not_called()
    else:
        assert response.json() == {
            "courseId": COURSE_ID, "columnId": COLUMN_ID,
            "userId": USER_ID_2, "score": 85.0,
        }
        connector.post_grade.assert_called_once_with("_course_1", COLUMN_ID, USER_ID_2, 85.0)
        connector.get_assessments.assert_not_called()


def test_INGEST_REQ_001_admin_retains_institution_gate(boundary, gradebook_request):
    client, user, _, reads, connector, gate, _ = boundary
    user.app_role = "admin"

    response = gradebook_request(client)

    assert response.status_code == 200
    gate.assert_called_once_with(user=user, course_id=COURSE_ID)
    assert [table for table, _ in reads] == ["courses"]
    assert len(connector.mock_calls) == 1


def test_INGEST_REQ_001_missing_course_retains_404(boundary, gradebook_request):
    client, _, enrollments, _, connector, _, courses = boundary
    enrollments.append(_enrollment())
    courses.clear()

    response = gradebook_request(client)

    assert response.status_code == 404
    assert response.json() == {"detail": "course not found"}
    assert connector.mock_calls == []


def test_INGEST_REQ_001_other_gate_errors_are_preserved(boundary, gradebook_request):
    client, _, _, reads, connector, gate, _ = boundary
    gate.side_effect = HTTPException(503, "authorization unavailable")

    response = gradebook_request(client)

    assert response.status_code == 503
    assert response.json() == {"detail": "authorization unavailable"}
    assert reads == []
    assert connector.mock_calls == []
