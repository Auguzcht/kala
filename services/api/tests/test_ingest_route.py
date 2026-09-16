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
            if params.get("tag_attempted_at") == "is.null":
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
    monkeypatch.setattr(diagnostic.bedrock, "embed", lambda text: [0.0] * 1024)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/course-1/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["stored"] == 1
    assert body["embedded"] == 1
    assert body["embedFailed"] == 0
    # Tagging left this endpoint for the worker's tag_backfill job, so the
    # response no longer reports tagged/remaining/complete. It reports how many
    # chunks the worker will pick up, which is observability, not a loop to
    # drive.
    assert body["tagging"] == "queued for the worker's tag_backfill job"
    assert "pendingTagging" in body
    assert "tagged" not in body
    assert "remaining" not in body

    assert inserted == [{
        "institution_id": "institution-1",
        "course_id": "course-1",
        "lms_ref": "lesson-1",
        "parent_lms_ref": "folder-1",
        "folder_path": [{"lmsRef": "folder-1", "title": "Module 1"}],
        "module_ref": "Module 1",
        "chunk_text": "[name]\nActual lesson content.",
    }]
    assert any("embedding" in u for u in updates)
    # No skill_id / tag_attempted_at / module_ref writes: tagging (and its
    # skill->module inference) runs in the worker's tag_backfill job now, not
    # on this request path.
    assert not any("skill_id" in u for u in updates)
    assert not any("tag_attempted_at" in u for u in updates)
    assert not any("module_ref" in u for u in updates)


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
    assert not any("embedding" in u for u in updates)
    # Tagging is the worker's now, so this path writes no skill_id either way.
    assert not any("skill_id" in u for u in updates)


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
            # The dedupe lookup is now ONE query returning every stored
            # lms_ref, so it reports lesson-1 as already present.
            if params.get("lms_ref") == "not.is.null":
                return [{"lms_ref": "lesson-1"}]
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


def test_retag_reopens_only_unmatched_content(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="admin",
    )
    reopened = []

    def fake_select(table, params):
        if table == "content_items":
            # The reset query asks for unmatched AND already-attempted.
            if params.get("tag_attempted_at") == "not.is.null":
                return [{"id": "unmatched-1"}, {"id": "unmatched-2"}]
            return [{"id": "unmatched-1"}, {"id": "unmatched-2"}]  # still unmatched
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(
        diagnostic.db, "update",
        lambda table, filters, values: reopened.append((filters, values)) or [],
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/course-1/content/retag")
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["reopened"] == 2
    assert body["pendingAfterReset"] == 2
    # Clears the mark and nothing else — never touches skill_id, so an
    # existing correct match cannot be disturbed.
    assert all(v == {"tag_attempted_at": None} for _, v in reopened)
    assert not any("skill_id" in v for _, v in reopened)


def test_retag_requires_staff(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="s", institution_id="institution-1", app_role="student",
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/course-1/content/retag")
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
            r = client.post("/courses/course-1/content/retag")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


def test_retag_is_a_noop_when_everything_matched(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="admin",
    )
    monkeypatch.setattr(diagnostic.db, "select", lambda table, params: [])
    monkeypatch.setattr(diagnostic.db, "update", lambda t, f, v: [])

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/courses/course-1/content/retag")
    finally:
        app.dependency_overrides.clear()

    assert r.json()["reopened"] == 0
    assert r.json()["next"] == "nothing to retag"


def test_ingest_dedupes_with_one_query_not_one_per_item(monkeypatch) -> None:
    """The store phase used to do a db.select PER content item to decide
    "already stored?". This course has 178 items, so that was 178 sequential
    round trips inside a 30s Lambda — the store phase alone blew the ceiling
    before tagging began, which is why /ingest returned 503 at exactly 30.00s
    with no tagging work done. The dedupe set must be fetched once.

    Pinned by counting: the number of content_items SELECTs must not scale with
    the number of items."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1", institution_id="institution-1", app_role="instructor"
    )

    class ManyItems:
        def get_content(self, course_ref):
            return [
                {"lms_content_id": f"item-{i}", "title": f"Item {i}",
                 "body_or_description": "body text", "content_type": "resource/x-bb-document",
                 "parent_id": None}
                for i in range(40)
            ]

    app.dependency_overrides[get_lms_connector] = ManyItems

    selects = {"content_items": 0}

    def fake_select(table, params):
        if table == "courses":
            return [{"lms_course_id": "_4_1"}]
        if table == "skills":
            return [{"id": "skill-1", "name": "Algebra"}]
        if table == "content_items":
            selects["content_items"] += 1
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

    assert response.status_code == 200
    # 40 items must not mean 40 dedupe lookups. A handful of phase queries is
    # expected (dedupe set, pending embeds, pending tags, remaining); what is
    # forbidden is growth with item count.
    assert selects["content_items"] < 10, (
        f"{selects['content_items']} content_items queries for 40 items — "
        "the dedupe lookup is scaling per item again and will time out"
    )
