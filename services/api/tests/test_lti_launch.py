"""Launch-level roster sync tests. Masterplan 3.1 (roster via LTI NRPS):
when an instructor or admin launches, the full class list is pulled from
the LMS and enrolled — so the cohort exists before each student has
individually opened Kala. A student launch never triggers the pull."""
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import get_lms_connector
from app.lti import claims as C
from app.lti import routes as lti_routes
from app.main import app


def _launch_payload(role_uris: list[str], *, sub: str = "lms-teacher-1") -> dict:
    s = get_settings()
    deployment_id = (s.deployment_id_list or [""])[0]
    return {
        "iss": "https://blackboard.com",
        "sub": sub,
        C.MESSAGE_TYPE: C.EXPECTED_MESSAGE_TYPE,
        C.DEPLOYMENT_ID: deployment_id,
        C.ROLES: role_uris,
        "nonce": "nonce-1",
        "name": "Prof. Ada",
        C.CONTEXT: {"id": "ctx-1", "label": "ME301", "title": "Thermo I"},
    }


def _fake_connector(roster: list[dict], content: list[dict] | None = None):
    class FakeConnector:
        def __init__(self) -> None:
            self.roster_calls = 0
            self.content_calls = 0
            self.content = content or [
                {"lms_content_id": "lesson-1", "body_or_description": "Module 1 content here."},
            ]

        def resolve_course_ref(self, external_id: str) -> str:
            return f"ref-{external_id}"

        def get_roster(self, course_ref: str) -> list[dict]:
            self.roster_calls += 1
            return roster

        def get_content(self, course_ref: str) -> list[dict]:
            self.content_calls += 1
            return self.content

    return FakeConnector()


def _patch_launch(monkeypatch, payload: dict, connector) -> dict:
    """Wire the launch handler to a crafted id_token + fake connector, and
    record db writes. Returns the recorded enrollments."""
    enrollments: list[dict] = []
    users: list[dict] = []
    monkeypatch.setattr(lti_routes, "verify_state", lambda cookie: {"state": "state-1", "nonce": "nonce-1"})
    monkeypatch.setattr(lti_routes, "verify_id_token", lambda token: payload)
    monkeypatch.setattr(lti_routes.db, "get_or_create_institution", lambda **kw: {"id": "inst-1"})

    def fake_upsert_user(*, lms_user_id: str, role: str, **kw) -> dict:
        users.append({"lms_user_id": lms_user_id, "role": role})
        return {"id": f"user-{lms_user_id}"}

    monkeypatch.setattr(lti_routes.db, "upsert_user", fake_upsert_user)
    monkeypatch.setattr(lti_routes.db, "get_or_create_course", lambda **kw: {"id": "course-1"})

    def fake_upsert_enrollment(*, user_id: str, course_id: str, role: str, **kw) -> None:
        enrollments.append({"user_id": user_id, "role": role})

    monkeypatch.setattr(lti_routes.db, "upsert_enrollment", fake_upsert_enrollment)
    app.dependency_overrides[get_lms_connector] = lambda: connector
    return {"enrollments": enrollments, "users": users}


def _launch(connector) -> TestClient:
    with TestClient(app) as client:
        return client.post(
            "/lti/launch",
            data={"id_token": "signed-token", "state": "state-1"},
            cookies={"kala_lti_state": "signed-state"},
            follow_redirects=False,  # the 302 goes to the SPA origin; don't chase it
        )


def test_instructor_launch_enrolls_students_who_have_never_launched(monkeypatch) -> None:
    roster = [
        {"lms_user_id": "stu-1", "role": "Student", "name": "Mica V.", "email": "m@mmcm.edu"},
        {"lms_user_id": "stu-2", "role": "Student", "name": "Raf C.", "email": "r@mmcm.edu"},
        {"lms_user_id": "ta-1", "role": "Teaching Assistant", "name": "TA Sam", "email": None},
    ]
    connector = _fake_connector(roster)
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert "launch#" in response.headers["location"]
    # The launching instructor is enrolled.
    assert {"user_id": "user-lms-teacher-1", "role": "instructor"} in recorded["enrollments"]
    # Every roster member was upserted + enrolled, students as students,
    # non-students coerced to instructor — none of them ever launched.
    assert recorded["users"][0] == {"lms_user_id": "lms-teacher-1", "role": "instructor"}
    for expected in [
        {"lms_user_id": "stu-1", "role": "student"},
        {"lms_user_id": "stu-2", "role": "student"},
        {"lms_user_id": "ta-1", "role": "instructor"},
    ]:
        assert expected in recorded["users"]
    assert {"user_id": "user-stu-1", "role": "student"} in recorded["enrollments"]
    assert {"user_id": "user-stu-2", "role": "student"} in recorded["enrollments"]
    assert {"user_id": "user-ta-1", "role": "instructor"} in recorded["enrollments"]


def test_student_launch_does_not_pull_the_roster(monkeypatch) -> None:
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_LEARNER], sub="lms-stu-1")
    recorded = _patch_launch(monkeypatch, payload, connector)

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert connector.roster_calls == 0
    assert {"user_id": "user-lms-stu-1", "role": "student"} in recorded["enrollments"]


def test_roster_failure_does_not_block_the_instructor_launch(monkeypatch) -> None:
    class BrokenConnector:
        def resolve_course_ref(self, external_id: str) -> str:
            return f"ref-{external_id}"

        def get_roster(self, course_ref: str) -> list[dict]:
            raise RuntimeError("LMS unreachable")

    connector = BrokenConnector()
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    # The instructor still lands; only the roster sync was skipped.
    assert {"user_id": "user-lms-teacher-1", "role": "instructor"} in recorded["enrollments"]


def test_instructor_launch_seeds_skills_when_course_has_none(monkeypatch) -> None:
    """BE-1 (skill pipeline): an instructor launch on a course with no skills
    pulls the course content and calls the proposer."""
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)
    seed_calls: list[dict] = []
    monkeypatch.setattr(lti_routes.db, "select", lambda t, p: [])  # no skills yet
    monkeypatch.setattr(
        lti_routes, "seed_course_skills",
        lambda **kw: seed_calls.append(kw) or {"skipped": False, "proposed": 1},
    )

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert connector.content_calls == 1
    assert len(seed_calls) == 1
    assert seed_calls[0]["institution_id"] == "inst-1"
    assert seed_calls[0]["course_id"] == "course-1"
    # Raw content items pass through (the proposer groups by module itself).
    assert seed_calls[0]["content_items"][0]["body_or_description"] == "Module 1 content here."
    assert "course_content" not in seed_calls[0]


def test_student_launch_does_not_seed_skills(monkeypatch) -> None:
    """Students launching never trigger skill proposals (or a content fetch)."""
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_LEARNER], sub="lms-stu-1")
    recorded = _patch_launch(monkeypatch, payload, connector)
    seed_calls: list[dict] = []
    monkeypatch.setattr(
        lti_routes, "seed_course_skills",
        lambda **kw: seed_calls.append(kw) or {"skipped": True},
    )

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert connector.content_calls == 0
    assert seed_calls == []
    assert {"user_id": "user-lms-stu-1", "role": "student"} in recorded["enrollments"]


def test_skill_seed_failure_does_not_block_the_launch(monkeypatch) -> None:
    """A proposer exception degrades to a normal launch (same contract as
    roster sync): the instructor still lands, the 302 is never delayed or
    replaced by an error."""
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)
    monkeypatch.setattr(lti_routes.db, "select", lambda t, p: [])
    monkeypatch.setattr(lti_routes, "seed_course_skills", lambda **kw: (_ for _ in ()).throw(RuntimeError("model unreachable")))

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert {"user_id": "user-lms-teacher-1", "role": "instructor"} in recorded["enrollments"]
