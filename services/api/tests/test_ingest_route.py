from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import diagnostic


class IngestConnector:
    def get_content(self, course_ref: str) -> list[dict]:
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
        ]


def test_ingest_uses_claim_tenant_and_finishes_embedding(monkeypatch) -> None:
    inserted = []
    updates = []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(
        diagnostic.db,
        "select",
        lambda table, params: (
            [{"lms_course_id": "_4_1"}]
            if table == "courses"
            else [{"id": "skill-1", "name": "Algebra"}]
        ),
    )
    monkeypatch.setattr(
        diagnostic.db,
        "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "content-row-1"}],
    )
    monkeypatch.setattr(diagnostic.db, "update", lambda table, filters, values: updates.append(values) or [])
    monkeypatch.setattr(
        diagnostic.model_router,
        "tag_content",
        lambda text, skills: {"skill_id": "skill-1", "bloom_level": "apply"},
    )
    monkeypatch.setattr(diagnostic.bedrock, "embed", lambda text: [0.0] * 1024)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"stored": 1, "tagged": 1, "embedded": 1, "embedFailed": 0}
    assert inserted == [{
        "institution_id": "institution-1",
        "course_id": "course-1",
        "lms_ref": "lesson-1",
        "parent_lms_ref": "folder-1",
        "folder_path": [{"lmsRef": "folder-1", "title": "Module 1"}],
        "module_ref": "Module 1",
        "chunk_text": "[name]\nActual lesson content.",
    }]
    assert {"skill_id": "skill-1"} in updates
    assert {"embedding": [0.0] * 1024} in updates
    # The tagged skill's module is backfilled from the content item it was
    # tagged from (skill-1 has no prior module_ref, so this fills the gap).
    assert {"module_ref": "Module 1"} in updates

def test_ingest_survives_an_embedding_provider_failure(monkeypatch) -> None:
    """A broken/timing-out embedding provider must not fail the whole ingest
    request (found necessary live: OpenRouter's free embedding endpoint was
    500ing and previously took the entire /ingest call down with it on the
    very first chunk). The content row and its skill tag are stored either
    way; only that chunk's embedding is skipped."""
    inserted = []
    updates = []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(
        diagnostic.db, "select",
        lambda table, params: (
            [{"lms_course_id": "_4_1"}] if table == "courses"
            else [{"id": "skill-1", "name": "Algebra"}]
        ),
    )
    monkeypatch.setattr(
        diagnostic.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "content-row-1"}],
    )
    monkeypatch.setattr(diagnostic.db, "update", lambda table, filters, values: updates.append(values) or [])
    monkeypatch.setattr(
        diagnostic.model_router, "tag_content",
        lambda text, skills: {"skill_id": "skill-1", "bloom_level": "apply"},
    )

    def flaky_embed(text):
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(diagnostic.bedrock, "embed", flaky_embed)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200  # not a 502, the request survives
    assert response.json() == {"stored": 1, "tagged": 1, "embedded": 0, "embedFailed": 1}
    # The content row and its skill tag were still stored, only the
    # embedding step for that chunk was skipped.
    assert inserted[0]["lms_ref"] == "lesson-1"
    assert {"skill_id": "skill-1"} in updates
    assert not any("embedding" in u for u in updates)


def test_propose_skills_endpoint_requires_instructor_or_admin(monkeypatch) -> None:
    """No relaunch needed to trigger skill proposal, but it's still
    instructor/admin only, same as everything else in this pipeline."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="student-1", institution_id="institution-1", app_role="student"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/skills/propose")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_propose_skills_endpoint_calls_the_proposer_with_fresh_content(monkeypatch) -> None:
    """The standalone endpoint fetches content fresh from the connector and
    hands it straight to seed_course_skills, same pipeline the launch
    handler uses, just callable on demand instead of only on a fresh
    Blackboard launch."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(
        diagnostic.db, "select",
        lambda table, params: [{"lms_course_id": "_4_1"}] if table == "courses" else [],
    )
    captured = {}

    def fake_seed(*, institution_id, course_id, content_items):
        captured["institution_id"] = institution_id
        captured["course_id"] = course_id
        captured["content_items"] = content_items
        return {"skipped": False, "modulesProcessed": 1, "proposed": 2,
                "auto_approved": 0, "flagged_possible_duplicate": 0}

    monkeypatch.setattr(diagnostic, "seed_course_skills", fake_seed)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/skills/propose")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["proposed"] == 2
    assert captured["institution_id"] == "institution-1"
    assert captured["course_id"] == "course-1"
    assert captured["content_items"][1]["lms_content_id"] == "lesson-1"
