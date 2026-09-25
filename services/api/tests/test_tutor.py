from app.deps import CurrentUser
from app.routers import tutor


def test_persisted_tutor_turns_have_matching_bulk_insert_keys(monkeypatch) -> None:
    """The nullable user style still has to be present in a bulk insert.

    PostgREST rejects an array whose objects have different key sets with
    PGRST102, even when the omitted column is nullable.
    """
    inserted = []

    def fake_select(table, _params):
        if table == "tutor_conversations":
            return [{
                "id": "00000000-0000-4000-8000-000000000060",
                "course_id": "00000000-0000-4000-8000-000000000001",
                "skill_id": None,
                "title": None,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }]
        return []

    def fake_insert(table, rows):
        assert table == "tutor_messages"
        assert len({frozenset(row) for row in rows}) == 1
        inserted.extend(rows)
        return rows

    monkeypatch.setattr(tutor.db, "select", fake_select)
    monkeypatch.setattr(tutor.db, "insert", fake_insert)
    monkeypatch.setattr(tutor.db, "update", lambda *args, **kwargs: [])
    monkeypatch.setattr(tutor.rag, "retrieve", lambda **kwargs: [])
    monkeypatch.setattr(tutor.model_router, "answer", lambda **kwargs: "An answer")

    result = tutor._ask(
        tutor.Ask(
            course_id="00000000-0000-4000-8000-000000000001",
            question="What is recursion?",
            style="detail",
            conversation_id="00000000-0000-4000-8000-000000000060",
        ),
        CurrentUser(
            user_id="00000000-0000-4000-8000-000000000040",
            institution_id="00000000-0000-4000-8000-000000000050",
            app_role="student",
        ),
    )

    assert result == {
        "answer": "An answer",
        "conversationId": "00000000-0000-4000-8000-000000000060",
    }
    assert inserted[0]["style"] is None
    assert inserted[1]["style"] == "detail"
