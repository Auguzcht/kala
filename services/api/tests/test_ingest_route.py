from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.main import app
from app.routers import diagnostic


class IngestConnector:
    def get_content(self, course_ref: str) -> list[dict]:
        return [
            {"lms_content_id": "folder-1", "body_or_description": "", "content_type": "resource/x-bb-folder"},
            {"lms_content_id": "lesson-1", "body_or_description": "name: Jane\nActual lesson content."},
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
    assert response.json() == {"stored": 1, "tagged": 1, "embedded": 1}
    assert inserted == [{
        "institution_id": "institution-1",
        "course_id": "course-1",
        "lms_ref": "lesson-1",
        "chunk_text": "[name]\nActual lesson content.",
    }]
    assert {"skill_id": "skill-1"} in updates
    assert {"embedding": [0.0] * 1024} in updates