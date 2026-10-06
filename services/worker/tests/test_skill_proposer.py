from app import skill_proposer


def test_module_is_not_marked_or_written_when_a_later_window_fails(monkeypatch):
    inserts = []
    updates = []
    calls = {"model": 0}

    def select(table, params):
        if table == "content_items":
            return [
                {"id": "a", "chunk_text": "A" * 8000, "embedding": [1.0, 0.0],
                 "module_ref": "m1", "created_at": "2026-01-01T00:00:00+00:00"},
                {"id": "b", "chunk_text": "B" * 8000, "embedding": [1.0, 0.0],
                 "module_ref": "m1", "created_at": "2026-01-01T00:00:00+00:00"},
            ]
        if table == "skills":
            return []
        raise AssertionError(table)

    monkeypatch.setattr(skill_proposer.db, "select", select)
    monkeypatch.setattr(skill_proposer.db, "insert", lambda *args, **kwargs: inserts.append(args) or [])
    monkeypatch.setattr(skill_proposer.db, "update", lambda *args, **kwargs: updates.append(args) or [])
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda *args, **kwargs: [])
    monkeypatch.setattr(skill_proposer.embed, "embed", lambda *args, **kwargs: [1.0, 0.0])

    def fail_on_second(_text):
        calls["model"] += 1
        if calls["model"] == 2:
            raise RuntimeError("timeout")
        return ([{"name": "Configure a load balancer", "bloom_level": "apply", "weight": 1.0}], 0)

    monkeypatch.setattr(skill_proposer, "_model", fail_on_second)
    result = skill_proposer.run(course_id="course-1", institution_id="inst-1", remaining_seconds=100)

    assert calls["model"] == 2
    assert result["modulesProcessed"] == 0
    assert result["remaining"] is True
    assert inserts == []
    assert updates == []
