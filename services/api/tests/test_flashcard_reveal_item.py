from app.learn import items as item_gen


def test_reveal_returns_correct_label_without_a_client_choice(monkeypatch) -> None:
    monkeypatch.setattr(
        item_gen.db, "select",
        lambda table, params: [{
            "id": "item-1", "skill_id": "skill-1", "course_id": "course-1",
            "correct_choice_id": "b", "explanation": "because b",
            "choices": [{"id": "a", "label": "Wrong"}, {"id": "b", "label": "Right"}],
        }],
    )
    out = item_gen.reveal(institution_id="inst-1", item_id="item-1")
    assert out == {
        "skillId": "skill-1", "courseId": "course-1",
        "correctChoiceId": "b", "correctLabel": "Right",
        "explanation": "because b",
    }


def test_reveal_raises_on_unknown_item(monkeypatch) -> None:
    monkeypatch.setattr(item_gen.db, "select", lambda table, params: [])
    try:
        item_gen.reveal(institution_id="inst-1", item_id="missing")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reveal_tolerates_a_missing_choice_label(monkeypatch) -> None:
    """Defensive: if choices somehow don't include the correct_choice_id (bad
    data), reveal degrades to a null label rather than crashing the endpoint."""
    monkeypatch.setattr(
        item_gen.db, "select",
        lambda table, params: [{
            "id": "item-1", "skill_id": "skill-1", "course_id": "course-1",
            "correct_choice_id": "z", "explanation": "",
            "choices": [{"id": "a", "label": "Wrong"}],
        }],
    )
    out = item_gen.reveal(institution_id="inst-1", item_id="item-1")
    assert out["correctLabel"] is None
