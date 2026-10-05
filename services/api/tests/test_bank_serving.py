from app.bank import serving


def test_bank_enabled_requires_course_flag_and_surface() -> None:
    assert serving.bank_enabled({"bank_serving": True}, "study")
    assert not serving.bank_enabled({"bank_serving": False}, "study")
    assert serving.bank_enabled({"bank_serving": True}, "test")


def test_pick_bank_items_is_db_only_and_excludes_tracked(monkeypatch) -> None:
    calls = []

    def select(table, params):
        calls.append(table)
        if table == "generated_items":
            return [
                {"id": "a", "source_chunk_ids": ["chunk-a"]},
                {"id": "b", "source_chunk_ids": ["chunk-b"]},
            ]
        if table == "srs_state":
            return [{"item_id": "a", "skill_id": "skill"}]
        return []

    monkeypatch.setattr(serving.db, "select", select)
    result = serving.pick_bank_items("user", "course", "skill", 5, "study", institution_id="inst")
    assert [item["id"] for item in result] == ["b"]
    assert calls == ["generated_items", "srs_state"]
