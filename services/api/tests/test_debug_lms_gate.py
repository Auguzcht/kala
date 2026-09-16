"""The debug LMS routes echo raw third-party payloads and take a caller-supplied
course_id, so "gated" has to mean staff-of-THIS-course, not staff-anywhere.
These tests pin both layers of that gate; the routes themselves are temporary
and tracked for removal, but a mis-gated temporary route is still a leak.
"""
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import debug_lms


def _user(role: str) -> CurrentUser:
    return CurrentUser(user_id="user-1", institution_id="inst-1", app_role=role)


def _client(user: CurrentUser) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: user
    # raise_server_exceptions=False: these tests assert on the GATE, so a
    # downstream LMS/DB failure must not mask the status the gate produced.
    return TestClient(app, raise_server_exceptions=False)


def test_student_is_rejected_by_the_role_layer(monkeypatch) -> None:
    """A student never reaches the teaches-course check."""
    client = _client(_user("student"))
    try:
        r = client.get("/debug/lms/item-raw/course-1/_530_1")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code in (401, 403)


def test_instructor_of_another_course_gets_404(monkeypatch) -> None:
    """The important case: holding an instructor role somewhere must not grant
    access to a different course's Blackboard tree."""
    monkeypatch.setattr(debug_lms.db, "select", lambda table, params: [])
    client = _client(_user("instructor"))
    try:
        r = client.get("/debug/lms/item-raw/course-other/_530_1")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


def test_instructor_of_this_course_passes_both_layers(monkeypatch) -> None:
    def fake_select(table, params):
        if table == "enrollments":
            return [{"course_id": "course-1"}]
        if table == "courses":
            return [{"lms_course_id": "_262_1"}]
        return []

    monkeypatch.setattr(debug_lms.db, "select", fake_select)
    # Stop before the real LMS call — the gate is what this test is about.
    import httpx
    def boom(*a, **k):
        raise httpx.ConnectError("no lms in tests")
    monkeypatch.setattr(httpx, "get", boom)

    client = _client(_user("instructor"))
    try:
        r = client.get("/debug/lms/item-raw/course-1/_530_1")
    finally:
        app.dependency_overrides.clear()
    # It got past authorization (anything but 401/403/404 from the gate).
    assert r.status_code not in (401, 403, 404)


def test_admin_does_not_need_a_course_enrollment(monkeypatch) -> None:
    def fake_select(table, params):
        if table == "courses":
            return [{"lms_course_id": "_262_1"}]
        # No enrollment row for the admin.
        return []

    monkeypatch.setattr(debug_lms.db, "select", fake_select)
    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(
        httpx.ConnectError("no lms in tests")))
    client = _client(_user("admin"))
    try:
        r = client.get("/debug/lms/item-raw/course-1/_530_1")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code not in (401, 403, 404)
