from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import diagnostic, ingest_jobs


class IngestConnector:
    def get_content(self, course_ref: str, *, include_attachments: bool = False, max_attachments: int = 3):
        return [
            {
                "lms_content_id": "folder-1", "title": "Module 1",
                "body_or_description": "", "content_type": "resource/x-bb-folder",
                "parent_id": None,
            },
            {
                "lms_content_id": "lesson-1", "title": "Lesson 1",
                "body_or_description": "name: Jane\nActual lesson content.",
                "parent_id": "folder-1",
            },
        ], {"fetched": 0, "skipped_unsupported": 0, "failed": 0, "capped": 0, "remaining": 0, "chunks": 0}


# ---------------------------------------------------------------------------
# /ingest now ENQUEUES instead of walking the tree inline. The walk itself
# (store, embed, dedupe, folder_path scoping) moved to the worker's
# ingest_walk job and is tested there (services/worker/tests/test_ingest_walk.py).
# These tests cover only the api-side contract: enqueue is O(1) and never
# calls Blackboard, a double-enqueue is a no-op that returns the live job
# rather than erroring, and the status route reflects the job row. Mirrors
# the original patch note's own "Tests" checklist for this route.
# ---------------------------------------------------------------------------

def test_ingest_enqueues_a_job_and_returns_202(monkeypatch) -> None:
    """No Blackboard call, no content_items write — POST /ingest is now just
    a row write. get_lms_connector is deliberately NOT overridden here: if
    the route reached for a connector at all, resolving it with no override
    would error, which is exactly the regression this test guards against."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )

    inserted = []

    def fake_select(table, params):
        assert table == "ingest_jobs"
        return []  # no live job yet

    def fake_insert(table, rows, prefer="return=representation"):
        assert table == "ingest_jobs"
        row = {
            "id": "job-1", "status": "pending",
            "include_attachments": rows[0]["include_attachments"],
            "folders_expanded": 0, "items_stored": 0, "pdfs_fetched": 0,
        }
        inserted.append(rows[0])
        return [row]

    monkeypatch.setattr(ingest_jobs.db, "select", fake_select)
    monkeypatch.setattr(ingest_jobs.db, "insert", fake_insert)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/courses/00000000-0000-4000-8000-000000000001/ingest",
                params={"include_attachments": "true"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["job"]["id"] == "job-1"
    assert body["job"]["created"] is True
    assert inserted == [{
        "institution_id": "institution-1",
        "course_id": "00000000-0000-4000-8000-000000000001",
        "status": "pending",
        "include_attachments": True,
    }]


def test_ingest_default_include_attachments_is_false(monkeypatch) -> None:
    """include_attachments defaults False — same default-cheap contract
    get_content() already had — when the caller doesn't pass the query param."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )
    inserted = []
    monkeypatch.setattr(ingest_jobs.db, "select", lambda table, params: [])
    monkeypatch.setattr(
        ingest_jobs.db, "insert",
        lambda table, rows, prefer="return=representation": (
            inserted.extend(rows) or [{
                "id": "job-2", "status": "pending",
                "include_attachments": rows[0]["include_attachments"],
                "folders_expanded": 0, "items_stored": 0, "pdfs_fetched": 0,
            }]
        ),
    )

    try:
        with TestClient(app) as client:
            response = client.post("/courses/00000000-0000-4000-8000-000000000001/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert inserted[0]["include_attachments"] is False


def test_ingest_double_enqueue_is_a_noop_returning_the_live_job(monkeypatch) -> None:
    """A second POST while one job is already pending/in_progress must not
    spawn a second walk against Blackboard's quota — it returns the SAME
    job, still 202 (nothing new started, but nothing failed either)."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )

    live_job = {
        "id": "already-live", "status": "in_progress", "include_attachments": False,
        "folders_expanded": 3, "items_stored": 7, "pdfs_fetched": 0,
    }

    def insert_should_not_be_called(*args, **kwargs):
        raise AssertionError("insert must not be called when a live job already exists")

    monkeypatch.setattr(ingest_jobs.db, "select", lambda table, params: [live_job])
    monkeypatch.setattr(ingest_jobs.db, "insert", insert_should_not_be_called)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/00000000-0000-4000-8000-000000000001/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "already_in_progress"
    assert body["job"]["id"] == "already-live"
    assert body["job"]["created"] is False


def test_ingest_status_route_reports_never_ingested(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )
    monkeypatch.setattr(ingest_jobs.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/courses/00000000-0000-4000-8000-000000000001/ingest/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "never_ingested"
    assert body["job"] is None


def test_ingest_status_route_reflects_the_job_row(monkeypatch) -> None:
    """Drives the row directly (no live Blackboard), per the original patch
    note's testing instructions: never_ingested -> pending -> complete as the
    row advances, is exactly what the worker's checkpoints produce live."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )
    row = {
        "id": "job-3", "status": "in_progress", "frontier": ["folder-9"],
        "folders_expanded": 5, "items_stored": 12, "pdfs_fetched": 1,
        "last_error": None, "created_at": "2026-01-01T00:00:00Z",
        "started_at": "2026-01-01T00:00:01Z", "updated_at": "2026-01-01T00:05:00Z",
        "finished_at": None,
    }
    monkeypatch.setattr(ingest_jobs.db, "select", lambda table, params: [row])

    try:
        with TestClient(app) as client:
            response = client.get("/courses/00000000-0000-4000-8000-000000000001/ingest/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["job"]["id"] == "job-3"
    assert body["job"]["items_stored"] == 12


def test_propose_skills_endpoint_requires_instructor_or_admin(monkeypatch) -> None:
    """No relaunch needed to trigger skill proposal, but it's still
    instructor/admin only, same as everything else in this pipeline."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="student-1", institution_id="institution-1", app_role="student"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    try:
        with TestClient(app) as client:
            response = client.post("/courses/00000000-0000-4000-8000-000000000001/skills/propose")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_propose_skills_endpoint_queues_without_model_or_content_calls(monkeypatch) -> None:
    """Proposal work belongs to the worker, never the request path."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(
        diagnostic.db, "select",
        lambda table, params: [{"lms_course_id": "_4_1"}] if table == "courses" else [],
    )
    kick_calls = []
    monkeypatch.setattr(diagnostic, "kick_bank", lambda course_id, trigger: kick_calls.append((course_id, trigger)))

    try:
        with TestClient(app) as client:
            response = client.post("/courses/00000000-0000-4000-8000-000000000001/skills/propose")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert kick_calls == [("00000000-0000-4000-8000-000000000001", "propose")]


def test_retag_runs_embedding_recompute_and_returns_counts(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="admin",
    )
    monkeypatch.setattr(diagnostic.tagging, "tag_recompute", lambda **kwargs: {
        "tagged": 7, "below_threshold": 3, "ambiguous": 2,
    })

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/00000000-0000-4000-8000-000000000001/content/retag")
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["tagged"] == 7
    assert body["belowThreshold"] == 3
    assert body["ambiguous"] == 2


def test_retag_requires_staff(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="s", institution_id="institution-1", app_role="student",
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/00000000-0000-4000-8000-000000000001/content/retag")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


def test_retag_rejects_an_instructor_of_another_course(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="i", institution_id="institution-1", app_role="instructor",
    )
    monkeypatch.setattr(diagnostic.db, "select", lambda table, params: [])
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/00000000-0000-4000-8000-000000000001/content/retag")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


def test_retag_returns_zero_counts_when_nothing_matches(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="admin",
    )
    monkeypatch.setattr(diagnostic.tagging, "tag_recompute", lambda **kwargs: {})

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/00000000-0000-4000-8000-000000000001/content/retag")
    finally:
        app.dependency_overrides.clear()

    assert r.json()["tagged"] == 0
    assert r.json()["belowThreshold"] == 0
    assert r.json()["ambiguous"] == 0


# The old per-item dedupe-scaling test (test_ingest_dedupes_with_one_query_
# not_one_per_item) is REMOVED, not ported: its premise was that /ingest's
# own request handler scanned content_items, which no longer happens at all
# now that the route only enqueues. That guarantee (one dedupe query, not one
# per item) still matters — it moved with the store loop into the worker and
# is covered there by ingest_walk's _existing_refs() and its tests.
