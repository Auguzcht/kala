"""AUTH-REQ-006: real identity/roster code with synthetic persistence/HTTP."""
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest

from app.db import supabase as db
from app.lms import blackboard
from app.lms.blackboard import BlackboardConnector
from app.lti.routes import _sync_roster


class Store:
    def __init__(self):
        self.tables = {n: [] for n in ("users", "user_profiles", "lms_identity_aliases", "enrollments", "evidence_events")}

    @staticmethod
    def matches(row, filters):
        for key, value in filters.items():
            if key in {"select", "limit", "order"}:
                continue
            if value.startswith("eq.") and str(row.get(key)) != value[3:]:
                return False
            if value.startswith("not.in.(") and str(row.get(key)) in value[8:-1].split(","):
                return False
        return True

    def select(self, table, params):
        assert not (table == "user_profiles" and "email" in params), "no email identity discovery"
        rows = [deepcopy(r) for r in self.tables[table] if self.matches(r, params)]
        return rows[:int(params.get("limit", len(rows)))]

    def upsert(self, table, rows, *, on_conflict):
        assert table != "evidence_events"
        result = []
        for value in rows:
            row = next((r for r in self.tables[table] if all(r.get(k) == value.get(k) for k in on_conflict.split(","))), None)
            if row is None:
                row = dict(value)
                if table == "users":
                    row["id"] = f"person-{len(self.tables[table]) + 1}"
                self.tables[table].append(row)
            else:
                row.update(value)
            result.append(deepcopy(row))
        return result

    def delete(self, table, filters):
        assert table == "enrollments", "only enrollment can be removed"
        removed = [r for r in self.tables[table] if self.matches(r, filters)]
        self.tables[table] = [r for r in self.tables[table] if not self.matches(r, filters)]
        return removed


@pytest.fixture
def store(monkeypatch):
    state = Store()
    for method in ("select", "upsert", "delete"):
        monkeypatch.setattr(db, method, getattr(state, method))
    return state


def resolve(subject="subject-a", institution="tenant-a", email=None, role="student"):
    return db.resolve_user(institution_id=institution, lms_user_id=subject,
                           role=role, display_name="Same synthetic name", email=email)


def launch(subject="subject-a", institution="tenant-a", email=None):
    user = resolve(subject, institution, email)
    db.upsert_enrollment(institution_id=institution, user_id=user["id"], course_id="course-a", role="student")
    return user


def member(subject="subject-a", email=None):
    return {"lms_user_id": subject, "role": "Student", "name": "Same synthetic name", "email": email}


def sync(members, institution="tenant-a", connector=None):
    return _sync_roster(institution_id=institution, course_id="course-a", course_ref="course-ref",
                        connector=connector or SimpleNamespace(get_roster=lambda _: members))


def evidence(store, *users):
    for user in users:
        store.tables["evidence_events"].append({"user_id": user["id"], "value": "synthetic history"})
    return deepcopy(store.tables["evidence_events"])


def assert_counts_only(caplog):
    records = [r for r in caplog.records if r.name in {"app.lti.routes", "app.lms.blackboard"}]
    assert records
    for record in records:
        assert not record.exc_info
        assert all(isinstance(value, int) for value in record.args)
        assert not any(value in record.getMessage() for value in (
            "private payload", "subject-a", "course-ref", "tenant-a", "http", "synthetic name",
        ))


@pytest.mark.parametrize("first", ["student", "instructor"])
def test_AUTH_REQ_006_either_order_repeated_sync_and_returning_launch(store, first):
    if first == "instructor":
        sync([member()])
    user = launch(email="first@example.test")
    before = evidence(store, user)
    for _ in range(3):
        assert sync([member()]) == {"enrolled": 1, "removed": 0}
        assert launch(email="changed@example.test")["id"] == user["id"]
    assert len(store.tables["users"]) == len(store.tables["enrollments"]) == 1
    assert store.tables["evidence_events"] == before


def test_AUTH_REQ_006_same_name_and_email_never_join_distinct_people(store):
    first = launch(email="shared@example.test")
    before = evidence(store, first)
    sync([member(email="shared@example.test"), member("subject-b", email="shared@example.test")])
    second = launch("subject-b", email="shared@example.test")
    assert first["id"] != second["id"]
    assert len(store.tables["users"]) == len(store.tables["enrollments"]) == 2
    assert store.tables["evidence_events"] == before


def test_AUTH_REQ_006_cross_institution_isolation(store):
    first = launch(email="shared@example.test")
    second = launch(institution="tenant-b", email="shared@example.test")
    before = evidence(store, first, second)
    sync([member()], institution="tenant-b")
    assert first["id"] != second["id"]
    assert len(store.tables["users"]) == len(store.tables["enrollments"]) == 2
    assert store.tables["evidence_events"] == before


def test_AUTH_REQ_006_legacy_rest_id_loses_enrollment_but_keeps_history(store):
    legacy = launch("rest-id", email="same@example.test")
    current = launch(email="same@example.test")
    before = evidence(store, legacy, current)
    aliases = deepcopy(store.tables["lms_identity_aliases"])
    assert sync([member(email="same@example.test")]) == {"enrolled": 1, "removed": 1}
    assert [r["user_id"] for r in store.tables["enrollments"]] == [current["id"]]
    assert len(store.tables["users"]) == 2
    assert store.tables["lms_identity_aliases"] == aliases
    assert store.tables["evidence_events"] == before


def test_AUTH_REQ_006_removed_instructor_loses_only_course_enrollment(store):
    departed = resolve("departed", role="instructor")
    other_tenant = resolve("departed", institution="tenant-b", role="instructor")
    for course in ("course-a", "course-b"):
        db.upsert_enrollment(institution_id="tenant-a", user_id=departed["id"], course_id=course, role="instructor")
    db.upsert_enrollment(institution_id="tenant-b", user_id=other_tenant["id"], course_id="course-a", role="instructor")
    before = evidence(store, departed, other_tenant)
    assert sync([member()])["removed"] == 1
    assert {(r["institution_id"], r["course_id"]) for r in store.tables["enrollments"]
            if r["user_id"] == departed["id"]} == {("tenant-a", "course-b")}
    assert any(r["user_id"] == other_tenant["id"] for r in store.tables["enrollments"])
    assert store.tables["evidence_events"] == before


@pytest.mark.parametrize("failure", ["resolution", "enrollment", "missing_identity"])
def test_AUTH_REQ_006_member_failure_removes_nobody(store, monkeypatch, caplog, failure):
    old = launch("old")
    before = evidence(store, old)
    enrolled_before = deepcopy(store.tables["enrollments"])
    def fail(**_):
        raise ValueError("private payload")
    if failure == "resolution":
        monkeypatch.setattr(db, "resolve_user", fail)
    elif failure == "enrollment":
        monkeypatch.setattr(db, "upsert_enrollment", fail)
    result = sync([member(), member(None)] if failure == "missing_identity" else [member()])
    assert result["skipped"] == "member_failed"
    assert result["removed"] == 0
    assert all(r in store.tables["enrollments"] for r in enrolled_before)
    assert store.tables["evidence_events"] == before
    assert_counts_only(caplog)


def test_AUTH_REQ_006_conflicting_alias_is_untouched(store):
    first, second = resolve(), resolve("subject-b")
    store.tables["lms_identity_aliases"][0]["user_id"] = second["id"]
    before = deepcopy(store.tables)
    with pytest.raises(ValueError, match="conflicting LMS identity"):
        resolve()
    assert store.tables == before
    assert first["id"] != second["id"]


def test_AUTH_REQ_006_exact_user_without_alias_ignores_email(store):
    first = resolve(email="first@example.test")
    resolve("subject-b", email="second@example.test")
    store.tables["lms_identity_aliases"].clear()
    assert resolve(email="second@example.test")["id"] == first["id"]
    assert len(store.tables["users"]) == 2


@pytest.fixture
def connector(monkeypatch):
    settings = SimpleNamespace(lms_rest_base_url="https://learn.example.test/learn/api/public/v1", lms_verify_tls=True)
    monkeypatch.setattr(blackboard, "get_settings", lambda: settings)
    reader = BlackboardConnector()
    monkeypatch.setattr(reader, "_headers", dict)
    return reader


def raw_member(uuid="subject-a"):
    return {"userId": "rest-id", "courseRoleId": "Student", "user": {
        "id": "rest-id", "uuid": uuid, "userName": "synthetic-username", "name": {}, "contact": {},
    }}


def response(body, status=200):
    return httpx.Response(status, json=body, request=httpx.Request("GET", "https://learn.example.test/roster"))


def test_AUTH_REQ_006_rest_uuid_matches_launch_sub_across_pages(store, connector, monkeypatch):
    user = launch()
    before = evidence(store, user)
    calls = []
    def get(path, **kwargs):
        calls.append((path, kwargs))
        if len(calls) == 1:
            return response({"results": [raw_member()], "paging": {"nextPage": "/learn/api/public/v1/courses/course-ref/users?offset=1"}})
        return response({"results": [raw_member("subject-b")]})
    monkeypatch.setattr(blackboard.httpx, "get", get)
    assert sync(None, connector=connector) == {"enrolled": 2, "removed": 0}
    assert "user.uuid" in calls[0][1]["params"]["fields"]
    assert calls[1][0] == "https://learn.example.test/learn/api/public/v1/courses/course-ref/users?offset=1"
    assert calls[1][1]["params"] is None
    assert resolve()["id"] == user["id"]
    assert len(store.tables["users"]) == 2
    assert store.tables["evidence_events"] == before


@pytest.mark.parametrize("kind", ["first_page_error", "later_page_error", "partial_status", "missing_results", "missing_uuid", "empty_uuid", "bad_paging", "bad_paging_container", "cycle", "foreign_origin", "error_body", "empty"])
def test_AUTH_REQ_006_incomplete_pull_removes_nobody(store, connector, monkeypatch, caplog, kind):
    old = launch("old")
    evidence(store, old)
    before = deepcopy(store.tables)
    calls = []
    def get(path, **kwargs):
        calls.append(path)
        if kind == "first_page_error" or (kind == "later_page_error" and len(calls) == 2):
            return response({"error": "private payload"}, status=503)
        if kind == "missing_results":
            return response({"paging": {}})
        if kind == "partial_status":
            return response({"results": [raw_member()]}, status=206)
        if kind in {"missing_uuid", "empty_uuid"}:
            return response({"results": [raw_member(None if kind == "missing_uuid" else "")]})
        if kind == "bad_paging":
            return response({"results": [raw_member()], "paging": {"nextPage": 3}})
        if kind == "bad_paging_container":
            return response({"results": [raw_member()], "paging": []})
        if kind == "foreign_origin":
            return response({"results": [raw_member()], "paging": {"nextPage": "https://foreign.example.test/roster"}})
        if kind == "error_body":
            return response({"results": [raw_member()], "errors": ["private payload"]})
        if kind == "empty":
            return response({"results": []})
        return response({"results": [raw_member()], "paging": {"nextPage": "/learn/api/public/v1/courses/course-ref/users?offset=1"}})
    monkeypatch.setattr(blackboard.httpx, "get", get)
    result = sync(None, connector=connector)
    assert result["removed"] == 0
    assert result["skipped"] in {"pull_failed", "empty_pull"}
    assert store.tables == before
    assert_counts_only(caplog)


def test_AUTH_REQ_006_removal_failure_skips_cooldown(store, monkeypatch, caplog):
    launch()
    def fail(*args, **kwargs):
        raise RuntimeError("private payload")
    monkeypatch.setattr(db, "delete", fail)
    assert sync([member()]) == {"enrolled": 1, "removed": 0, "skipped": "removal_failed"}
    assert_counts_only(caplog)


@pytest.mark.parametrize("terminal", [{}, {"paging": None}, {"paging": {}}, {"paging": {"nextPage": None}}, {"paging": {"nextPage": ""}}])
def test_AUTH_REQ_006_terminal_paging_forms_complete_successfully(store, connector, monkeypatch, terminal):
    launch("old")
    monkeypatch.setattr(blackboard.httpx, "get", lambda *args, **kwargs: response({"results": [raw_member()], **terminal}))
    assert sync(None, connector=connector) == {"enrolled": 1, "removed": 1}


def test_AUTH_REQ_006_low_quota_warning_contains_counts_only(store, connector, monkeypatch, caplog):
    page = response({"results": [raw_member()]})
    page.headers["X-Rate-Limit-Remaining"] = "12"
    monkeypatch.setattr(blackboard.httpx, "get", lambda *args, **kwargs: page)
    assert sync(None, connector=connector) == {"enrolled": 1, "removed": 0}
    assert_counts_only(caplog)
