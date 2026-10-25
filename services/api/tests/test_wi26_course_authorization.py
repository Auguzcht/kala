"""WI-26 admission matrix: real role/course guards, synthetic persistence only."""
from unittest.mock import Mock

import pytest
from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import bank, courses, dashboard, diagnostic, twin
from fastapi.testclient import TestClient

C = "00000000-0000-4000-8000-000000000001"
I = "00000000-0000-4000-8000-000000000002"
FOREIGN = "00000000-0000-4000-8000-000000000003"
U = "00000000-0000-4000-8000-000000000040"
S = "00000000-0000-4000-8000-000000000042"
SK = "00000000-0000-4000-8000-000000000010"
R = "00000000-0000-4000-8000-000000000050"
STAFF = [
    ("GET", f"/dashboard/{C}/heatmap", None),
    ("GET", f"/dashboard/{C}/at-risk", None),
    ("GET", f"/dashboard/{C}/roster", None),
    ("GET", f"/dashboard/{C}/stats", None),
    ("GET", f"/dashboard/{C}/students/{S}/twin", None),
    ("GET", f"/dashboard/{C}/students/{S}/record", None),
    ("GET", f"/dashboard/{C}/students/{S}/recommendations", None),
    ("POST", f"/dashboard/{C}/students/{S}/recommendations", None),
    ("POST", f"/dashboard/{C}/students/{S}/interventions", {"title": "Practice"}),
    ("PATCH", f"/dashboard/{C}/recommendations/{R}", {"status": "approved"}),
    ("GET", f"/dashboard/{C}/skills/proposed", None),
    ("GET", f"/dashboard/{C}/skills/auto-matched", None),
    ("PATCH", f"/dashboard/{C}/skills/{SK}/review", {"status": "approved"}),
    ("PATCH", f"/dashboard/{C}/skills/{SK}/detach", None),
    ("POST", f"/dashboard/{C}/skills/{SK}/reject-approved", None),
    ("POST", f"/courses/{C}/skills/propose", None),
    ("GET", f"/courses/{C}/roster", None),
    ("POST", f"/courses/{C}/ingest", None),
    ("GET", f"/courses/{C}/ingest/status", None),
    ("POST", f"/courses/{C}/content/upload", None),
    ("POST", f"/courses/{C}/content/retag", None),
    ("GET", f"/courses/{C}/assessments", None),
    ("PATCH", f"/courses/{C}/assessments/{SK}/grade", {"user_id": S, "score": 85}),
]
SHARED = [("GET", f"/courses/{C}{suffix}", None) for suffix in
          ("", "/memory/summary", "/twin", "/next-up", "/plan", "/bank/status", "/content", "/modules", "/diagnostic", "/diagnostic/status")]
SHARED.append(("POST", f"/courses/{C}/diagnostic/submit", {"answers": [{"item_id": SK, "choice_id": "a"}]}))


@pytest.fixture
def boundary(monkeypatch):
    user = CurrentUser(U, I, "instructor")
    state = {"teaches": True, "target": True, "rec_course": C, "rec_institution": I, "moved": False, "changed": 0}
    protected = []
    admission = []

    def select(table, params):
        if table == "enrollments" and params.get("role") == "eq.instructor":
            admission.append((table, params))
            assert params["institution_id"] == f"eq.{user.institution_id}"
            assert params["user_id"] == f"eq.{U}"
            assert params["course_id"] == f"eq.{C}"
            return [{"course_id": C}] if state["teaches"] and user.institution_id == I else []
        if table == "courses":
            admission.append((table, params))
            assert params["institution_id"] == f"eq.{user.institution_id}"
            assert params["id"] == f"eq.{C}"
            return [{"id": C, "lms_course_id": "synthetic-course", "title": "Synthetic", "bank_serving": {}}] if user.institution_id == I else []
        if table == "recommendations" and params.get("select") == "user_id":
            admission.append(("recommendation-lookup", params))
            assert params == {"id": f"eq.{R}", "institution_id": f"eq.{user.institution_id}",
                              "course_id": f"eq.{C}", "select": "user_id", "limit": "1"}
            return [{"user_id": S}] if state["rec_course"] == C and state["rec_institution"] == user.institution_id else []
        if table == "enrollments" and user.app_role == "student":
            return [{"user_id": U}]
        protected.append(("select", table))
        if table == "users":
            return [{"id": S, "role": "student", "pseudonym": "Synthetic"}]
        return []

    def operation(kind, result):
        def run(*args, **kwargs):
            protected.append((kind, args))
            return result
        return run

    monkeypatch.setattr(dashboard.db, "select", select)
    def update(table, filters, values):
        protected.append(("update", (table, filters, values)))
        if table == "recommendations":
            assert filters == {"id": f"eq.{R}", "institution_id": f"eq.{I}",
                               "course_id": f"eq.{C}", "user_id": f"eq.{S}"}
            if state["moved"]:
                return []
            state["changed"] += 1
        return [{"id": R, "user_id": S, "course_id": C, **values}]
    monkeypatch.setattr(dashboard.db, "update", update)
    monkeypatch.setattr(dashboard.db, "insert", operation("insert", [{"id": R, "user_id": S, "course_id": C}]))
    monkeypatch.setattr(dashboard.db, "upsert", operation("queue", []))
    monkeypatch.setattr(dashboard.db, "rpc", operation("rpc", [{"retired_items": 1}]))
    monkeypatch.setattr(dashboard, "kick_bank", operation("kick", None))
    monkeypatch.setattr(diagnostic, "kick_bank", operation("kick", None))
    monkeypatch.setattr(bank, "kick_bank", operation("kick", None))
    monkeypatch.setattr(dashboard.cohort, "student_ids", lambda **kw: [S] if state["target"] else [])
    monkeypatch.setattr(dashboard.cohort, "roster", operation("roster", {"students": []}))
    monkeypatch.setattr(dashboard.cohort, "stats", operation("stats", {}))
    monkeypatch.setattr(dashboard.cohort, "load_identities", operation("identities", {}))
    monkeypatch.setattr(dashboard.cohort, "learner_record", operation("record", {"pseudonym": "Synthetic"}))
    monkeypatch.setattr(dashboard.summary, "twin_payload", operation("twin", {"skills": [], "evidence": []}))
    monkeypatch.setattr(dashboard.prescriber, "recommend", operation("model", ([], "synthetic")))
    monkeypatch.setattr(twin.item_gen, "weakest_skill", operation("next", None))
    monkeypatch.setattr(courses.srs, "new_remaining_today", operation("memory", 0))
    monkeypatch.setattr(diagnostic, "enqueue_ingest", operation("ingest-queue", {"created": True, "status": "pending"}))
    monkeypatch.setattr(diagnostic, "ingest_job_status", operation("ingest-status", None))
    monkeypatch.setattr(diagnostic.tagging, "tag_recompute", operation("retag", {}))
    monkeypatch.setattr(diagnostic.storage, "upload", operation("storage", None))
    monkeypatch.setattr(diagnostic.documents, "extract_text", operation("extract", "Synthetic text"))
    monkeypatch.setattr(diagnostic.bedrock, "embed", operation("embed", [0.0] * 1024))
    monkeypatch.setattr(diagnostic, "_diagnostic_availability", operation("availability", {"items": [], "pendingSkillIds": [], "failedSkillIds": [], "waitingForMaterialCount": 0}))
    monkeypatch.setattr(diagnostic.item_gen, "grade", operation("grade", {"skillId": SK, "correct": True, "explanation": "Synthetic"}))
    monkeypatch.setattr(diagnostic, "record_exposure", operation("exposure", None))
    monkeypatch.setattr(diagnostic.db, "insert_evidence", operation("evidence", None))
    monkeypatch.setattr(diagnostic.tracer, "apply_evidence", operation("tracer", {"estimate": 0.6}))
    connector = Mock()
    connector.get_roster.side_effect = operation("lms-roster", [])
    connector.get_content.side_effect = operation("lms-content", ([], {}))
    connector.get_assessments.side_effect = operation("lms-read", [])
    connector.post_grade.side_effect = operation("lms-write", None)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_lms_connector] = lambda: connector
    try:
        with TestClient(app) as client:
            yield client, user, state, protected, admission
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize("route", STAFF + SHARED, ids=lambda r: r[0] + r[1])
@pytest.mark.parametrize("actor", ["student", "other-teacher", "foreign-teacher", "foreign-admin", "teacher", "admin"])
def test_admission_matrix(boundary, route, actor):
    client, user, state, protected, admission = boundary
    user.app_role = "student" if actor == "student" else ("admin" if "admin" in actor else "instructor")
    state["teaches"] = actor not in {"other-teacher", "foreign-teacher"}
    if actor.startswith("foreign"):
        user.institution_id = FOREIGN
    method, path, body = route
    if path.endswith("/content/upload"):
        response = client.request(method, path, files={"file": ("synthetic.txt", b"Synthetic text", "text/plain")})
    else:
        response = client.request(method, path, json=body)
    shared = route in SHARED
    allowed = actor in {"teacher", "admin"} or (actor == "student" and shared)
    expected = (202 if path.endswith(("/skills/propose", "/ingest")) else 200) if allowed else (403 if actor == "student" else 404)
    assert response.status_code == expected, response.text
    if not allowed:
        assert protected == [], "denial must precede all learning reads/writes and external operations"
        if actor == "student":
            assert admission == []
    if path.endswith("/skills/propose") and allowed:
        assert [p[0] for p in protected] == ["queue", "kick"]
    if allowed and actor != "student":
        assert any(table == "courses" for table, _ in admission)
        if actor == "teacher":
            assert any(table == "enrollments" for table, _ in admission)


@pytest.mark.parametrize("route", [r for r in STAFF if "/students/" in r[1]])
def test_learner_routes_refuse_unenrolled_target_before_learning_data(boundary, route):
    client, _, state, protected, _ = boundary
    state["target"] = False
    method, path, body = route
    response = client.request(method, path, json=body)
    assert response.status_code == 404
    assert protected == []


@pytest.mark.parametrize("failure", ["foreign-course", "foreign-institution", "unenrolled", "moved"])
def test_recommendation_scoped_lookup_and_bound_update(boundary, failure):
    client, _, state, protected, admission = boundary
    if failure == "foreign-course":
        state["rec_course"] = SK
    elif failure == "foreign-institution":
        state["rec_institution"] = FOREIGN
    elif failure == "unenrolled":
        state["target"] = False
    else:
        state["moved"] = True
    response = client.patch(f"/dashboard/{C}/recommendations/{R}", json={"status": "approved"})
    assert response.status_code == 404
    assert state["changed"] == 0
    assert len([x for x in admission if x[0] == "recommendation-lookup"]) == 1
    assert protected == [] if failure != "moved" else len(protected) == 1 and protected[0][0] == "update"


@pytest.mark.parametrize("role", ["instructor", "admin"])
@pytest.mark.parametrize("decision", ["approved", "modified", "rejected"])
def test_recommendation_decisions_keep_semantics_and_mutate_once(boundary, role, decision):
    client, user, state, protected, admission = boundary
    user.app_role = role
    response = client.patch(f"/dashboard/{C}/recommendations/{R}", json={
        "status": decision, "decision_note": "synthetic decision", "instructor_note": "synthetic action",
    })
    assert response.status_code == 200
    assert response.json()["status"] == decision
    assert response.json()["decisionNote"] == "synthetic decision"
    assert response.json()["instructorNote"] == "synthetic action"
    assert response.json()["decidedBy"] == U
    assert state["changed"] == 1
    assert len([x for x in protected if x[0] == "update"]) == 1
    assert len([x for x in admission if x[0] == "recommendation-lookup"]) == 1
