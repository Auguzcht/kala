"""Staff upload of course content.

This endpoint exists because Blackboard's REST API exposes file items as
metadata only (verified live), so a course whose real material is PDFs has
nothing for ingest to read. These tests cover the gate and the storage path;
the extraction itself is covered by test_blackboard_content's sibling tests in
app/ai/documents.py.
"""
import io

from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic


def _staff(role="admin"):
    return CurrentUser(user_id="user-1", institution_id="institution-1", app_role=role)


def _wire(monkeypatch, *, inserted, updates, embedded_text=None):
    monkeypatch.setattr(
        diagnostic.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": f"row-{len(inserted)}"}],
    )
    monkeypatch.setattr(
        diagnostic.db, "update",
        lambda table, filters, values: updates.append((table, values)) or [],
    )

    # The tag query and the "how much is left" query filter on the SAME
    # condition, so the stub must drain once tagging has happened or the
    # endpoint will (correctly) report remaining=1 forever. Tag once, then
    # report nothing pending.
    state = {"tagged": False}

    def fake_select(table, params):
        if table == "skills":
            return [{"id": "skill-1", "name": "Cloud Concepts"}]
        if table == "content_items":
            if params.get("embedding") == "is.null":
                return [{"id": "row-1", "chunk_text": embedded_text or "body"}]
            if params.get("tag_attempted_at") == "is.null":
                if state["tagged"]:
                    return []
                state["tagged"] = True
                return [{"id": "row-1", "chunk_text": "body", "module_ref": None}]
            return []
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.storage, "upload", lambda *a, **k: None)
    monkeypatch.setattr(diagnostic.bedrock, "embed", lambda text: [0.0] * 1024)


def test_upload_rejects_a_student(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="s", institution_id="institution-1", app_role="student",
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("a.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


def test_upload_rejects_an_instructor_of_another_course(monkeypatch) -> None:
    """The gate that matters: staff somewhere is not staff here."""
    app.dependency_overrides[get_current_user] = lambda: _staff("instructor")
    monkeypatch.setattr(diagnostic.db, "select", lambda table, params: [])
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("a.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


def test_upload_rejects_an_unsupported_file_type(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: _staff()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("notes.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 415


def test_upload_rejects_a_file_with_no_extractable_text(monkeypatch) -> None:
    """A scanned/image-only PDF extracts to whitespace. Telling staff is right:
    they can act on it (OCR first), and silently storing a chunk-less file
    would look like success while contributing nothing to generation."""
    app.dependency_overrides[get_current_user] = lambda: _staff()
    monkeypatch.setattr(diagnostic.documents, "extract_text", lambda c, m: "   \n  ")
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("scan.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 422
    assert "no extractable text" in r.json()["detail"]


def test_upload_stores_extracted_text_as_course_content(monkeypatch) -> None:
    """The point of the endpoint: extracted text lands in content_items (the
    shared course corpus), not in the private per-student attachment table."""
    app.dependency_overrides[get_current_user] = lambda: _staff()
    inserted, updates = [], []
    _wire(monkeypatch, inserted=inserted, updates=updates)
    monkeypatch.setattr(
        diagnostic.documents, "extract_text",
        lambda c, m: "Managed services trade cost for operational overhead.",
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("deck.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
                data={"module_ref": "Module 2|Building Blocks of AWS"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["stored"] == 1
    assert body["filename"] == "deck.pdf"
    assert body["tagging"] == "queued for the worker's tag_backfill job"

    # Written to content_items with the course's tenant and the module the
    # uploader named, and lms_ref null because it has no LMS counterpart.
    assert inserted[0]["course_id"] == "course-1"
    assert inserted[0]["institution_id"] == "institution-1"
    assert inserted[0]["module_ref"] == "Module 2|Building Blocks of AWS"
    assert inserted[0]["lms_ref"] is None
    assert "Managed services" in inserted[0]["chunk_text"]


def test_upload_embeds_and_queues_tagging_for_the_worker(monkeypatch) -> None:
    """Uploads take the SAME store+embed path as ingest and then QUEUE tagging
    for the worker. Tagging used to run here; it is LLM-bound and moved off the
    request path (see the worker's tag_backfill job)."""
    app.dependency_overrides[get_current_user] = lambda: _staff()
    inserted, updates = [], []
    _wire(monkeypatch, inserted=inserted, updates=updates)
    monkeypatch.setattr(diagnostic.documents, "extract_text", lambda c, m: "body text here")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("deck.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    body = r.json()
    assert body["embedded"] == 1
    assert body["tagging"] == "queued for the worker's tag_backfill job"
    assert "pendingTagging" in body
    # No tag write happened on this request path.
    assert not any("skill_id" in v for (_, v) in updates)


def test_upload_archiving_failure_does_not_fail_the_upload(monkeypatch) -> None:
    """Storing the original is provenance, not the payload. If Storage is down,
    the extracted text still lands and the response says so."""
    app.dependency_overrides[get_current_user] = lambda: _staff()
    inserted, updates = [], []
    _wire(monkeypatch, inserted=inserted, updates=updates)
    monkeypatch.setattr(diagnostic.documents, "extract_text", lambda c, m: "body text")

    def boom(*a, **k):
        raise RuntimeError("storage down")

    monkeypatch.setattr(diagnostic.storage, "upload", boom)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post(
                "/courses/course-1/content/upload",
                files={"file": ("deck.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["originalArchived"] is False
    assert inserted, "the text must still be stored"
