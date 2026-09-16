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


def _phase_select(*, courses, skills, pending_embed=None, pending_tag=None):
    """A db.select stub that answers the ingest phases distinctly.

    The new ingest asks three different questions of content_items (which
    chunks exist for dedupe, which lack an embedding, which lack a skill), so a
    single catch-all lambda no longer models it. This dispatches on the filter.
    """
    def fake_select(table, params):
        if table == "courses":
            return courses
        if table == "skills":
            return skills
        if table == "content_items":
            # Dedupe check: filtered by lms_ref. Nothing present yet.
            if "lms_ref" in params:
                return []
            if params.get("embedding") == "is.null":
                return pending_embed or []
            if params.get("skill_id") == "is.null":
                return pending_tag or []
        return []
    return fake_select


def test_ingest_uses_claim_tenant_and_finishes_embedding(monkeypatch) -> None:
    inserted = []
    updates = []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(diagnostic.db, "select", _phase_select(
        courses=[{"lms_course_id": "_4_1"}],
        skills=[{"id": "skill-1", "name": "Algebra"}],
        # Phase 2/3 read back the row the store phase just wrote.
        pending_embed=[{"id": "content-row-1", "chunk_text": "[name]\nActual lesson content."}],
        pending_tag=[{"id": "content-row-1", "chunk_text": "[name]\nActual lesson content.",
                      "module_ref": "Module 1"}],
    ))
    monkeypatch.setattr(
        diagnostic.db, "insert",
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
    body = response.json()
    assert body["stored"] == 1
    assert body["tagged"] == 1
    assert body["embedded"] == 1
    assert body["embedFailed"] == 0
    # The response now reports whether the course is fully ingested, because a
    # bare 200 never meant "complete" (that is what the 5-chunk course taught).
    assert "remaining" in body and "complete" in body

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
    request. The content row and its skill tag are stored either way; only that
    chunk's embedding is skipped."""
    inserted = []
    updates = []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector
    monkeypatch.setattr(diagnostic.db, "select", _phase_select(
        courses=[{"lms_course_id": "_4_1"}],
        skills=[{"id": "skill-1", "name": "Algebra"}],
        pending_embed=[{"id": "content-row-1", "chunk_text": "lesson body"}],
        pending_tag=[{"id": "content-row-1", "chunk_text": "lesson body", "module_ref": "Module 1"}],
    ))
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
    body = response.json()
    assert body["embedded"] == 0
    assert body["embedFailed"] == 1
    assert inserted[0]["lms_ref"] == "lesson-1"
    assert {"skill_id": "skill-1"} in updates
    assert not any("embedding" in u for u in updates)


def test_ingest_skips_items_already_stored_so_a_rerun_does_not_duplicate(monkeypatch) -> None:
    """Resumability depends on this: re-running ingest after a timeout must
    pick up where it left off, not store every chunk again."""
    inserted = []

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector

    def fake_select(table, params):
        if table == "courses":
            return [{"lms_course_id": "_4_1"}]
        if table == "skills":
            return [{"id": "skill-1", "name": "Algebra"}]
        if table == "content_items":
            # The dedupe lookup reports lesson-1 is ALREADY stored.
            if "lms_ref" in params:
                return [{"id": "already-there"}]
            return []
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(
        diagnostic.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "new"}],
    )
    monkeypatch.setattr(diagnostic.db, "update", lambda table, filters, values: [])

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert inserted == [], "an already-stored item must not be inserted again"
    assert response.json()["stored"] == 0


def test_ingest_reports_remaining_when_tagging_is_incomplete(monkeypatch) -> None:
    """`complete: false` is how a caller learns to call again. A bare 200 used
    to be indistinguishable from a finished run — the exact confusion that let
    a 5-chunk course look ingested."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )
    app.dependency_overrides[get_lms_connector] = IngestConnector

    def fake_select(table, params):
        if table == "courses":
            return [{"lms_course_id": "_4_1"}]
        if table == "skills":
            return [{"id": "skill-1", "name": "Algebra"}]
        if table == "content_items":
            if "lms_ref" in params:
                return [{"id": "done"}]  # nothing new to store
            return []
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.db, "insert", lambda t, rows: [{"id": "x"}])
    monkeypatch.setattr(diagnostic.db, "update", lambda t, f, v: [])

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/ingest")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["complete"] is True
    assert body["remaining"] == 0


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
