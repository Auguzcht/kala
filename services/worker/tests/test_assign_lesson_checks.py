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
