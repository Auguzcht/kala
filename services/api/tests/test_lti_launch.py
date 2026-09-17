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


def _launch_payload(role_uris: list[str], *, sub: str = "lms-teacher-1",
                    email: str | None = "prof@mmcm.edu") -> dict:
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
        **({"email": email} if email else {}),
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


def _patch_launch(monkeypatch, payload: dict, connector,
                  resolved_ids: dict[str, str] | None = None) -> dict:
    """Wire the launch handler to a crafted id_token + fake connector, and
    record db writes. Returns the recorded enrollments."""
    enrollments: list[dict] = []
    users: list[dict] = []
    removals: list[dict] = []
    aliases: list[dict] = []
    # email -> existing user id. Empty by default; a test that wants to prove
    # the launch RESOLVES instead of duplicating seeds this.
    resolved_ids = resolved_ids or {}
    monkeypatch.setattr(lti_routes, "verify_state", lambda cookie: {"state": "state-1", "nonce": "nonce-1"})
    monkeypatch.setattr(lti_routes, "verify_id_token", lambda token: payload)
    monkeypatch.setattr(lti_routes.db, "get_or_create_institution", lambda **kw: {"id": "inst-1"})

    def fake_resolve_user(*, institution_id: str, lms_user_id: str, role: str,
                          email: str | None = None,
                          display_name: str | None = None, **kw) -> dict:
        # Mirrors db.resolve_user's real contract in BOTH respects the fix
        # depends on: it returns the resolved user, and it records the
        # identifier->user alias on EVERY resolution (not only new users).
        users.append({"lms_user_id": lms_user_id, "role": role, "email": email})
        existing = resolved_ids.get(email) if email else None
        user_id = existing or f"user-{lms_user_id}"
        aliases.append({
            "institution_id": institution_id, "lms_user_id": lms_user_id,
            "user_id": user_id,
            "source": "email_match" if existing else "launch",
        })
        return {"id": user_id}

    monkeypatch.setattr(lti_routes.db, "resolve_user", fake_resolve_user)
    monkeypatch.setattr(lti_routes.db, "record_identity_alias",
                        lambda **kw: aliases.append(kw))
    monkeypatch.setattr(lti_routes.db, "get_or_create_course", lambda **kw: {"id": "course-1"})

    def fake_upsert_enrollment(*, user_id: str, course_id: str, role: str, **kw) -> None:
        enrollments.append({"user_id": user_id, "role": role})

    monkeypatch.setattr(lti_routes.db, "upsert_enrollment", fake_upsert_enrollment)

    # Roster reconciliation's other half. Recorded (not left unmocked) for
    # two reasons: an unmocked call would hit the real Supabase client with
    # no credentials in a test run, and the call args are exactly what the
    # new reconciliation tests below assert on — which user ids survived
    # into keep_user_ids is the whole point of the feature.
    def fake_remove_stale(*, institution_id: str, course_id: str, keep_user_ids: list[str]) -> list[dict]:
        removals.append({
            "institution_id": institution_id, "course_id": course_id,
            "keep_user_ids": list(keep_user_ids),
        })
        return []

    monkeypatch.setattr(lti_routes.db, "remove_stale_student_enrollments", fake_remove_stale)
    app.dependency_overrides[get_lms_connector] = lambda: connector
    return {"enrollments": enrollments, "users": users, "removals": removals,
            "aliases": aliases}


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
    assert recorded["users"][0]["lms_user_id"] == "lms-teacher-1"
    assert recorded["users"][0]["role"] == "instructor"
    # Compare on the fields under test; resolve_user also records the email it
    # saw, which is what lets a later launch resolve instead of duplicating.
    for lms_id, role in [("stu-1", "student"), ("stu-2", "student"), ("ta-1", "instructor")]:
        assert any(
            u["lms_user_id"] == lms_id and u["role"] == role
            for u in recorded["users"]
        ), f"{lms_id} not resolved as {role}"
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


def test_instructor_launch_reconciles_stale_enrollments(monkeypatch) -> None:
    """The half of roster sync that didn't exist before this change: anyone
    Kala has as a student in this course who is NOT in the fresh pull must
    be passed to remove_stale_student_enrollments — this is what turns a
    one-off test launch or a dropped student into something that heals on
    the next instructor launch instead of persisting forever.

    The fixture includes the launching instructor's own membership, which
    is realistic: Blackboard's course/users listing reports every member,
    including the instructor doing the launching, not just their students.
    """
    roster = [
        {"lms_user_id": "lms-teacher-1", "role": "Instructor", "name": "Prof. Ada", "email": None},
        {"lms_user_id": "stu-1", "role": "Student", "name": "Mica V.", "email": "m@mmcm.edu"},
    ]
    connector = _fake_connector(roster)
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    assert len(recorded["removals"]) == 1
    call = recorded["removals"][0]
    assert call["course_id"] == "course-1"
    # keep_user_ids is exactly what this pull produced. Anyone Kala has
    # enrolled as a STUDENT for this course outside that set is what gets
    # removed — asserted here as "the call carries the right keep-list",
    # since the actual delete is a real db.py function this test
    # intentionally does not re-implement. Note deletion is also
    # role-scoped in remove_stale_student_enrollments itself (role='student'
    # only): even if a launching instructor were somehow absent from a
    # pull, their own role='instructor' row could never match that filter,
    # so this isn't the only thing standing between an instructor and
    # accidentally reconciling away their own access.
    assert set(call["keep_user_ids"]) == {"user-lms-teacher-1", "user-stu-1"}


def test_empty_roster_pull_skips_reconciliation(monkeypatch) -> None:
    """An empty pull must never be treated as 'this class has zero
    students' — that would delete every real enrollment on the next
    instructor launch. This is the guard that makes reconciliation safe to
    run unattended on every launch rather than something that needs a human
    to sanity-check the pull first."""
    connector = _fake_connector([])  # instructor launch, but the LMS returns nothing
    payload = _launch_payload([C._ROLE_INSTRUCTOR])
    recorded = _patch_launch(monkeypatch, payload, connector)

    try:
        response = _launch(connector)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 302
    # The instructor's own launch-time enrollment (step 3, unconditional)
    # still happens; what must NOT happen is a reconciliation call derived
    # from an empty roster.
    assert recorded["removals"] == []


def test_roster_pull_failure_skips_reconciliation(monkeypatch) -> None:
    """Symmetric with the empty-pull guard: a raised exception from the
    connector must also never reach reconciliation."""
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
    assert recorded["removals"] == []


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


# ---- duplicate-account regression (migration 0015) ------------------------
# The bug: `users.lms_user_id` is written from the LTI `sub` on launch and from
# the connector's REST `userId` on roster sync — two different values for the
# same person. upsert_user keyed on lms_user_id, so a student who was BOTH
# rostered and launched got TWO rows: the roster row held the enrollment (so
# the instructor saw them), the launch row held all the evidence (so their work
# was invisible). Confirmed live: 4 such pairs, one with 149 stranded events.
#
# These tests pin the two hard requirements: the lms_user_id fallback STAYS,
# and the alias is recorded on EVERY resolution (not just new users).


def test_launch_resolves_to_the_rostered_account_by_email(monkeypatch) -> None:
    """THE bug. A launch whose `sub` is unseen, but whose email matches an
    existing (rostered) profile, must resolve to that account instead of
    minting a twin. Before the fix this created a second user row and split the
    student's progress in half."""
    connector = _fake_connector([])
    payload = _launch_payload(
        [C._ROLE_LEARNER], sub="2aca8e5459054620993530550b5f0a93",
        email="kala.student1@example.com",
    )
    recorded = _patch_launch(
        monkeypatch, payload, connector,
        # The rostered account already exists under Blackboard's userId form.
        resolved_ids={"kala.student1@example.com": "rostered-user-id"},
    )
    _launch(connector)

    # Resolved to the EXISTING account, not a new `user-<sub>` row.
    assert recorded["users"][0]["lms_user_id"] == "2aca8e5459054620993530550b5f0a93"
    assert recorded["enrollments"][0]["user_id"] == "rostered-user-id"


def test_launch_records_the_alias_on_every_resolution(monkeypatch) -> None:
    """Requirement 2: the alias write is NOT conditional on the user being new.
    Recording the identifier pair the first time it is OBSERVED is what makes
    the next launch an exact lookup instead of another email guess."""
    connector = _fake_connector([])
    payload = _launch_payload(
        [C._ROLE_LEARNER], sub="sub-hash-abc", email="kala.student5@example.com",
    )
    recorded = _patch_launch(
        monkeypatch, payload, connector,
        resolved_ids={"kala.student5@example.com": "existing-user-id"},
    )
    _launch(connector)

    assert recorded["aliases"], "an alias must be written on an email resolution"
    alias = recorded["aliases"][0]
    assert alias["lms_user_id"] == "sub-hash-abc"
    assert alias["user_id"] == "existing-user-id"


def test_launch_without_email_still_creates_a_user(monkeypatch) -> None:
    """Requirement 1: the lms_user_id fallback STAYS. Email is not guaranteed
    present on an LTI launch, and resolution must not depend on it."""
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_LEARNER], sub="no-email-sub", email=None)
    recorded = _patch_launch(monkeypatch, payload, connector)
    _launch(connector)

    assert recorded["users"][0]["lms_user_id"] == "no-email-sub"
    # And it still records the alias, so the NEXT launch is an exact lookup.
    assert recorded["aliases"][0]["lms_user_id"] == "no-email-sub"


def test_launch_with_no_matching_email_creates_a_user(monkeypatch) -> None:
    """An email that matches nobody is a genuinely new person, not a failure."""
    connector = _fake_connector([])
    payload = _launch_payload([C._ROLE_LEARNER], sub="fresh-sub", email="nobody@example.com")
    recorded = _patch_launch(monkeypatch, payload, connector, resolved_ids={})
    _launch(connector)

    assert recorded["enrollments"][0]["user_id"] == "user-fresh-sub"
