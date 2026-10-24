"""APPROVAL-05 / WI-21: TUTOR-REQ-002/003. No network or real user data."""
from copy import deepcopy

import pytest
from conftest import CONVERSATION_ID, COURSE_ID, INSTITUTION_ID, USER_ID
from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import tutor

OTHER_USER = "00000000-0000-4000-8000-000000000041"
OTHER_INSTITUTION = "00000000-0000-4000-8000-000000000051"
UPDATED_AT = "2026-10-24T00:00:00+00:00"


@pytest.fixture
def management_client(monkeypatch):
    row = {
        "id": CONVERSATION_ID,
        "institution_id": INSTITUTION_ID,
        "user_id": USER_ID,
        "course_id": COURSE_ID,
        "skill_id": None,
        "title": "Original title",
        "pinned_at": "2026-10-23T00:00:00+00:00",
        "created_at": UPDATED_AT,
        "updated_at": UPDATED_AT,
    }
    calls = []

    def update(table, filters, changes):
        calls.append((table, filters, changes.copy()))
        if any(filters.get(key) != f"eq.{row[key]}" for key in (
            "id", "user_id", "institution_id",
        )):
            return []
        row.update(changes)
        if row["pinned_at"] == "now":
            row["pinned_at"] = f"2026-10-25T00:00:{len(calls):02d}+00:00"
        return [deepcopy(row)]

    monkeypatch.setattr(tutor.db, "update", update)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student",
    )
    try:
        with TestClient(app) as client:
            yield client, row, calls
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("title", ["x", "x" * 80])
def test_TUTOR_REQ_002_owner_rename_boundaries_preserve_pin_and_activity(management_client, title):
    client, row, calls = management_client
    before = deepcopy(row)
    response = client.patch(f"/tutor/conversations/{CONVERSATION_ID}", json={"title": title})
    assert response.status_code == 200
    assert response.json()["title"] == row["title"] == title
    assert response.json()["pinnedAt"] == before["pinned_at"]
    assert response.json()["updatedAt"] == before["updated_at"]
    assert calls == [("tutor_conversations", {
        "id": f"eq.{CONVERSATION_ID}",
        "user_id": f"eq.{USER_ID}",
        "institution_id": f"eq.{INSTITUTION_ID}",
    }, {"title": title})]


@pytest.mark.parametrize("foreign_field,foreign_value", [
    ("user_id", OTHER_USER), ("institution_id", OTHER_INSTITUTION),
    ("id", "00000000-0000-4000-8000-000000000061"),
])
@pytest.mark.parametrize("changes", [{"title": "Renamed"}, {"pinned": True}, {"pinned": False}])
def test_TUTOR_REQ_002_003_foreign_or_missing_conversation_404_without_mutation(
    management_client, foreign_field, foreign_value, changes,
):
    client, row, _calls = management_client
    row[foreign_field] = foreign_value
    before = deepcopy(row)
    response = client.patch(f"/tutor/conversations/{CONVERSATION_ID}", json=changes)
    assert response.status_code == 404
    assert response.json() == {"detail": "conversation not found"}
    assert row == before


def test_TUTOR_REQ_002_malformed_id_404_before_mutation(management_client):
    client, _row, calls = management_client
    response = client.patch("/tutor/conversations/not-a-uuid", json={"title": "Renamed"})
    assert response.status_code == 404
    assert calls == []


@pytest.mark.parametrize("changes", [
    {}, {"title": ""}, {"title": "x" * 81}, {"title": None}, {"title": 1},
    {"title": True}, {"pinned": None}, {"pinned": "true"}, {"pinned": 1},
    {"pinned": []}, {"institution_id": OTHER_INSTITUTION},
    {"title": "Valid", "user_id": OTHER_USER}, {"title": "Valid", "pinned": None},
    [], "title", None,
])
def test_TUTOR_REQ_002_003_invalid_body_422_without_mutation(management_client, changes):
    client, row, calls = management_client
    before = deepcopy(row)
    response = client.patch(f"/tutor/conversations/{CONVERSATION_ID}", json=changes)
    assert response.status_code == 422
    assert row == before
    assert calls == []


def test_TUTOR_REQ_003_pin_refresh_unpin_and_combined_rename(management_client):
    client, row, calls = management_client
    url = f"/tutor/conversations/{CONVERSATION_ID}"
    first = client.patch(url, json={"pinned": True})
    assert first.status_code == 200
    assert first.json()["pinnedAt"] == row["pinned_at"]
    assert first.json()["title"] == "Original title"
    second = client.patch(url, json={"pinned": True, "title": "New title"})
    assert second.status_code == 200
    assert second.json()["pinnedAt"] > first.json()["pinnedAt"]
    assert second.json()["title"] == row["title"] == "New title"
    assert calls[-1][2] == {"title": "New title", "pinned_at": "now"}
    assert all("updated_at" not in changes for _table, _filters, changes in calls)
    unpinned = client.patch(url, json={"pinned": False})
    assert unpinned.status_code == 200
    assert unpinned.json()["pinnedAt"] is row["pinned_at"] is None
    assert unpinned.json()["updatedAt"] == UPDATED_AT
    assert unpinned.json()["title"] == "New title"


def test_TUTOR_REQ_003_list_scopes_ordering_and_nullable_pin_projection(management_client, monkeypatch):
    client, row, _calls = management_client
    rows = [deepcopy(row), {**row, "id": "00000000-0000-4000-8000-000000000061", "pinned_at": None}]
    queries = []

    def select(table, params):
        queries.append((table, params.copy()))
        return rows

    monkeypatch.setattr(tutor.db, "select", select)
    response = client.get("/tutor/conversations", params={"course_id": COURSE_ID})
    assert response.status_code == 200
    conversations = response.json()["conversations"]
    assert [entry["pinnedAt"] for entry in conversations] == [row["pinned_at"], None]
    assert all(set(entry) == {
        "id", "courseId", "skillId", "title", "createdAt", "updatedAt", "pinnedAt",
    } for entry in conversations)
    assert queries == [("tutor_conversations", {
        "institution_id": f"eq.{INSTITUTION_ID}",
        "user_id": f"eq.{USER_ID}",
        "course_id": f"eq.{COURSE_ID}",
        "select": "id,course_id,skill_id,title,created_at,updated_at,pinned_at",
        "order": "pinned_at.desc.nullslast,updated_at.desc",
    })]


def test_TUTOR_REQ_003_empty_course_list_preserves_envelope(management_client, monkeypatch):
    client, _row, _calls = management_client
    monkeypatch.setattr(tutor.db, "select", lambda *args: [])
    response = client.get("/tutor/conversations", params={"course_id": COURSE_ID})
    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_TUTOR_REQ_002_003_create_and_detail_contracts_are_unchanged(management_client, monkeypatch):
    client, row, _calls = management_client
    monkeypatch.setattr(tutor.db, "insert", lambda *args: [row.copy()])
    monkeypatch.setattr(tutor.db, "select", lambda table, params: [row.copy()] if table == "tutor_conversations" else [])
    created = client.post("/tutor/conversations", json={"course_id": COURSE_ID})
    detail = client.get(f"/tutor/conversations/{CONVERSATION_ID}")
    assert created.status_code == detail.status_code == 200
    assert "pinnedAt" not in created.json()
    assert "pinnedAt" not in detail.json()
    assert detail.json() == {**created.json(), "messages": [], "attachments": []}


def test_TUTOR_REQ_002_003_openapi_patch_is_optional_nonnullable_and_strict(management_client):
    client, _row, _calls = management_client
    schema = client.get("/openapi.json").json()
    body = schema["components"]["schemas"]["ConversationPatch"]
    assert body["additionalProperties"] is False
    assert body["minProperties"] == 1
    assert "required" not in body
    assert body["properties"]["title"]["type"] == "string"
    assert body["properties"]["title"]["minLength"] == 1
    assert body["properties"]["title"]["maxLength"] == 80
    assert body["properties"]["pinned"]["type"] == "boolean"
