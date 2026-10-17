import pytest

from app.jobs import assign_lesson_checks


def test_assignment_checkpoints_each_step_and_is_resumable(monkeypatch):
    e1 = [1.0, 0.0] + [0.0] * 1022
    e2 = [0.0, 1.0] + [0.0] * 1022
    stored_steps = [
        {"id": "s1", "position": 0, "summary": "one", "detail_points": [],
         "bloom_level": "remember", "check_item_id": None, "embedding": e1},
        {"id": "s2", "position": 1, "summary": "two", "detail_points": [],
         "bloom_level": "remember", "check_item_id": None, "embedding": e2},
    ]
    items = [{"id": "i1", "embedding": e1, "bloom_level": "remember"}]
    writes = []

    def select(table, params):
        if table == "guided_lessons":
            return [{"id": "lesson", "course_id": "course", "skill_id": "skill"}]
        if table == "guided_lesson_steps":
            return stored_steps
        if table == "generated_items":
            return items
        raise AssertionError(table)

    def update(table, filters, values):
        writes.append((table, filters, values))
        if table == "worker_state":
            return [{"key": filters["key"]}]
        if table == "guided_lesson_steps":
            for step in stored_steps:
                if step["id"] == filters["id"].removeprefix("eq."):
                    step["check_item_id"] = values["check_item_id"]
            return [values]
        return []

    monkeypatch.setattr(assign_lesson_checks.db, "select", select)
    monkeypatch.setattr(assign_lesson_checks.db, "update", update)
    monkeypatch.setattr(assign_lesson_checks, "embed", lambda text: e1)

    first = assign_lesson_checks.run(lesson_id="lesson")
    second = assign_lesson_checks.run(lesson_id="lesson")

    assert first["assigned"] == 1
    assert second["assigned"] == 0
    assert [values["check_item_id"] for table, _, values in writes
            if table == "guided_lesson_steps" and "check_item_id" in values] == ["i1"]


def test_missing_step_and_item_embeddings_are_saved_and_reused(monkeypatch):
    vector = [1.0, 0.0] + [0.0] * 1022
    step = {"id": "s1", "position": 0, "summary": "one", "detail_points": [],
            "bloom_level": "remember", "check_item_id": None, "embedding": None}
    item = {"id": "i1", "prompt": "one", "bloom_level": "remember", "embedding": None}
    stored = {"guided_lesson_steps": [step], "generated_items": [item]}
    embedding_calls = []
    writes = []

    def select(table, params):
        if table == "guided_lessons":
            return [{"id": "lesson", "course_id": "course", "skill_id": "skill"}]
        if table == "guided_lesson_steps":
            return stored[table]
        if table == "generated_items":
            return stored[table]
        raise AssertionError(table)

    def update(table, filters, values):
        writes.append((table, filters, values))
        if table == "worker_state":
            return [{"key": filters["key"]}]
        row = stored[table][0]
        row.update(values)
        return [row]

    def fake_embed(text):
        embedding_calls.append(text)
        return vector

    monkeypatch.setattr(assign_lesson_checks.db, "select", select)
    monkeypatch.setattr(assign_lesson_checks.db, "update", update)
    monkeypatch.setattr(assign_lesson_checks, "embed", fake_embed)

    first = assign_lesson_checks.run(lesson_id="lesson")
    second = assign_lesson_checks.run(lesson_id="lesson")

    assert first["embedded_steps"] == 1
    assert first["embedded_items"] == 1
    assert len(embedding_calls) == 2
    assert second["embedded"] == 0
    assert len(embedding_calls) == 2
    assert any(table == "guided_lesson_steps" and "embedding" in values for table, _, values in writes)
    assert any(table == "generated_items" and "embedded_at" in values for table, _, values in writes)


def test_assignment_does_not_run_when_another_worker_holds_the_lease(monkeypatch):
    monkeypatch.setattr(assign_lesson_checks.db, "update", lambda *args: [])
    monkeypatch.setattr(assign_lesson_checks.db, "select", lambda *args: pytest.fail("must not read during a live lease"))
    result = assign_lesson_checks.run(lesson_id="lesson")
    assert result == {"lesson_id": "lesson", "assigned": 0, "already_running": True}
