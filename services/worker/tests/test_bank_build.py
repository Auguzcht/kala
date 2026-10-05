import json

from app.jobs import bank_build


def _item(prompt="What is the primary benefit of elasticity in cloud computing?"):
    return {"prompt": prompt, "choices": [
        {"id": "a", "label": "Scaling resources with demand"},
        {"id": "b", "label": "Buying fixed hardware"},
        {"id": "c", "label": "Removing all monitoring"},
        {"id": "d", "label": "Disabling automation"},
    ], "correct_choice_id": "a", "explanation": "It matches demand."}


def test_partial_batch_keeps_valid_items_and_rejects_duplicates():
    items = [_item(), _item("What is the primary benefit of elasticity in cloud computing today?"),
             _item("Which practice improves cloud cost visibility for a team?")]
    valid = bank_build._valid_items(items, [])
    assert len(valid) == 2


def test_duplicate_stem_hash_and_jaccard_are_rejected():
    item = _item()
    valid = bank_build._valid_items([item], [item["prompt"]])
    assert valid == []
    assert bank_build._stem_hash("Hello, cloud!") == bank_build._stem_hash("hello cloud")


def test_absolute_distractors_are_rejected():
    item = _item()
    item["choices"][1]["label"] = "It never needs monitoring"
    item["choices"][2]["label"] = "It always scales perfectly"
    assert bank_build._valid_items([item], []) == []


def test_batch_size_is_clamped_to_remaining_need(monkeypatch):
    captured = {}
    monkeypatch.setattr(bank_build, "_live_items", lambda *args: [{"prompt": "existing"}] * 3)
    monkeypatch.setattr(bank_build, "_call_model", lambda **kwargs: captured.update(kwargs) or ([], {}))
    state = {"course_id": "c", "skill_id": "s", "institution_id": "i", "name": "Cloud elasticity",
             "bloom_level": "understand", "mcq_target": 5, "deadline": 9999999999}
    bank_build._build_one(state, [{"id": "chunk", "text": "x" * 1200}], 0)
    assert captured["batch_size"] == 2


def test_choice_shuffle_preserves_correct_id_and_varies_position(monkeypatch):
    inserted = []
    monkeypatch.setattr(bank_build, "_live_items", lambda *args: [])
    monkeypatch.setattr(bank_build, "_call_model", lambda **kwargs: ([_item()], {}))
    monkeypatch.setattr(bank_build.db, "insert", lambda table, rows: inserted.extend(rows) or rows)
    state = {"course_id": "c", "skill_id": "s", "institution_id": "i", "name": "Cloud elasticity",
             "bloom_level": "understand", "mcq_target": 5, "deadline": 9999999999}
    for i in range(200):
        bank_build._build_one(state, [{"id": f"chunk-{i}", "text": "x" * 1200}], i)
    positions = [next(i for i, c in enumerate(row["choices"]) if c["id"] == row["correct_choice_id"]) for row in inserted]
    counts = [positions.count(i) for i in range(4)]
    assert all(20 <= count <= 80 for count in counts)


def test_breadth_first_pending_ordering():
    rows = [
        {"skill_id": "top-up", "depth": 10, "mcq_ready": 8, "mcq_target": 20},
        {"skill_id": "empty", "depth": 10, "mcq_ready": 0, "mcq_target": 20},
        {"skill_id": "usable", "depth": 10, "mcq_ready": 8, "mcq_target": 8},
    ]
    assert [row["skill_id"] for row in bank_build._pending(rows)] == ["empty", "top-up"]


def test_lease_is_one_conditional_update(monkeypatch):
    calls = []
    monkeypatch.setattr(bank_build.db, "update", lambda table, filters, values: calls.append((table, filters, values)) or [{"skill_id": "s"}])
    state = {"course_id": "c", "skill_id": "s", "mcq_target": 20}
    assert bank_build._lease(state)
    assert len(calls) == 1
    assert "and" in calls[0][1]
    assert "leased_until" in calls[0][2]


def test_bank_insert_payload_never_has_set_id(monkeypatch):
    inserted = []
    monkeypatch.setattr(bank_build, "_live_items", lambda *args: [])
    monkeypatch.setattr(bank_build, "_call_model", lambda **kwargs: ([_item()], {"status": "success"}))
    monkeypatch.setattr(bank_build.db, "insert", lambda table, rows: inserted.extend(rows) or rows)
    state = {"course_id": "c", "skill_id": "s", "institution_id": "i", "name": "Cloud elasticity", "bloom_level": "understand", "deadline": 9999999999}
    bank_build._build_one(state, [{"id": "chunk", "text": "x" * 1200}], 0)
    assert inserted and inserted[0]["origin"] == "bank"
    assert "set_id" not in inserted[0]


def test_insert_count_uses_rows_returned_by_supabase(monkeypatch):
    monkeypatch.setattr(bank_build, "_live_items", lambda *args: [])
    monkeypatch.setattr(bank_build, "_call_model", lambda **kwargs: ([_item()], {"status": "success"}))
    monkeypatch.setattr(bank_build.db, "insert", lambda table, rows: [])
    state = {"course_id": "c", "skill_id": "s", "institution_id": "i", "name": "Cloud elasticity", "bloom_level": "understand", "deadline": 9999999999}
    result = bank_build._build_one(state, [{"id": "chunk", "text": "x" * 1200}], 0)
    assert result["inserted"] == 0


def test_thin_context_makes_zero_model_calls(monkeypatch):
    called = []
    monkeypatch.setattr(bank_build, "_live_items", lambda *args: [])
    monkeypatch.setattr(bank_build, "_call_model", lambda **kwargs: called.append(kwargs) or ([], {}))
    state = {"course_id": "c", "skill_id": "s", "institution_id": "i", "name": "Cloud elasticity", "bloom_level": "understand", "deadline": 9999999999}
    try:
        bank_build._build_one(state, [{"id": "chunk", "text": "too short"}], 0)
    except bank_build.ThinContextError:
        pass
    else:
        raise AssertionError("thin context must fail before model invocation")
    assert called == []


def test_thin_context_policy_flips_to_building_when_context_grows():
    status, error, chars, chunks = bank_build._context_status(1, [{"id": "short", "text": "x" * 250}])
    assert (status, error, chars, chunks) == ("no_material", "thin: 250 chars across 1 chunks", 250, 1)
    status, error, chars, chunks = bank_build._context_status(1, [{"id": "long", "text": "x" * 1200}])
    assert (status, error, chars, chunks) == ("building", None, 1200, 1)


def test_failure_counter_increments_once(monkeypatch):
    updates = []
    monkeypatch.setattr(bank_build.db, "update", lambda table, filters, values: updates.append(values) or [])
    state = {"course_id": "c", "skill_id": "s", "consecutive_failures": 1}
    bank_build._record_failure(state, RuntimeError("failed"))
    assert updates[0]["consecutive_failures"] == 2


def test_non_stop_finish_is_failure(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"finish_reason": "length", "message": {"content": json.dumps({"items": []})}}]}
    class Client:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    monkeypatch.setattr(bank_build.httpx, "Client", Client)
    monkeypatch.setattr(bank_build, "get_settings", lambda: type("S", (), {"openrouter_model_bank": "m", "bank_reasoning_effort": "low", "openrouter_base_url": "https://x", "openrouter_api_key": "k"})())
    try:
        bank_build._call_model(skill={"name": "x"}, context="x", do_not_repeat=[], remaining=50)
    except RuntimeError as exc:
        assert "non-stop" in str(exc)
    else:
        raise AssertionError("non-stop response must fail")
