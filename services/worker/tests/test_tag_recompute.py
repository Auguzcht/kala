from app.jobs import tag_recompute


def test_recompute_uses_one_rpc_per_course_and_never_constructs_model(monkeypatch, caplog):
    calls = []
    monkeypatch.setattr(tag_recompute.db, "select", lambda table, params: (
        [{"id": "c1", "institution_id": "i1"}] if table == "courses" else
        [{"id": "s1", "name": "Skill one", "embedding": [0.1]}]
    ))
    monkeypatch.setattr(tag_recompute.db, "rpc", lambda fn, args: calls.append((fn, args)) or [{
        "tagged": 2, "below_threshold": 1, "ambiguous": 1, "changed": 2, "gap_filled": 1,
    }])
    result = tag_recompute.run(course_id="c1")
    assert result == {"courses": 1, "tagged": 2, "below_threshold": 1,
                     "ambiguous": 1, "changed": 2, "gap_filled": 1}
    assert len(calls) == 1
    assert calls[0][0] == "recompute_embedding_tags"
    assert calls[0][1]["p_threshold"] == 0.544
    assert calls[0][1]["p_min_margin"] == 0.03


def test_skill_without_embedding_is_warned_and_skipped(monkeypatch, caplog):
    monkeypatch.setattr(tag_recompute.db, "select", lambda table, params: (
        [{"id": "c1", "institution_id": "i1"}] if table == "courses" else
        [{"id": "s1", "name": "Missing", "embedding": None}]
    ))
    monkeypatch.setattr(tag_recompute.db, "rpc", lambda *args: [{
        "tagged": 0, "below_threshold": 2, "ambiguous": 0,
    }])
    with caplog.at_level("WARNING"):
        tag_recompute.run(course_id="c1")
    assert "skill_missing_embedding" in caplog.text
    assert "s1" in caplog.text
