import logging
from datetime import UTC, datetime

from app import skill_proposer


def _setup(monkeypatch, rows, *, cursors=None, existing=None):
    inserts, updates, saved = [], [], dict(cursors or {})
    persisted_skills = list(existing or [])

    def select(table, params):
        if table == "content_items":
            return rows
        if table == "skills":
            return list(persisted_skills)
        if table == "worker_state":
            key = params["key"].removeprefix("eq.")
            return [{"value": saved[key]}] if key in saved else []
        raise AssertionError(table)

    def insert(table, values):
        inserts.extend(values)
        persisted = [{**row, "id": f"saved-{len(inserts)}", "created_at": datetime.now(UTC).isoformat()} for row in values]
        persisted_skills.extend(persisted)
        return persisted

    def upsert(table, values, *, on_conflict):
        for value in values:
            saved[value["key"]] = value["value"]
        return values

    monkeypatch.setattr(skill_proposer.db, "select", select)
    monkeypatch.setattr(skill_proposer.db, "insert", insert)
    monkeypatch.setattr(skill_proposer.db, "upsert", upsert)
    monkeypatch.setattr(skill_proposer.db, "update", lambda *a, **k: updates.append((a, k)) or [])
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda *a, **k: [])
    monkeypatch.setattr(skill_proposer.embed, "embed", lambda *a, **k: [1.0, 0.0])
    return inserts, updates, saved


def _rows():
    return [
        {"id": str(i), "chunk_text": chr(65 + i) * 12000, "embedding": [1.0, 0.0],
         "module_ref": "m1", "created_at": "2026-01-01T00:00:00+00:00"}
        for i in range(4)
    ]


def test_window_cursor_resumes_after_mid_module_kill(monkeypatch):
    inserts, updates, saved = _setup(monkeypatch, _rows())
    count = 0

    def model(_):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("simulated kill")
        return ([{"name": f"Apply skill {count}", "bloom_level": "apply", "weight": 1}], [])

    monkeypatch.setattr(skill_proposer, "_model", model)
    out = skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert count == 2
    assert out["remaining"] is True
    assert len(inserts) == 1
    assert saved["proposer:c:m1"]["windows_completed"] == 1
    assert updates == []

    monkeypatch.setattr(skill_proposer, "_model", lambda _: ([{"name": "Apply next", "bloom_level": "apply"}], []))
    out = skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert out["modulesProcessed"] == 1
    assert saved["proposer:c:m1"]["windows_completed"] == 4
    assert len(inserts) == 1
    assert any(args[0] == "courses" for args, _ in updates)


def test_existing_two_window_cursor_resumes_at_window_three(monkeypatch):
    rows = _rows()
    # _windows creates four windows; the checkpoint must resume exactly at 3.
    key = "proposer:c:m1"
    freshness = skill_proposer._freshness(rows)
    inserts, _, saved = _setup(monkeypatch, rows, cursors={key: {"windows_completed": 2, "content_freshness": freshness}})
    calls = []
    monkeypatch.setattr(skill_proposer, "_model", lambda _: calls.append(1) or ([], []))
    skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert len(calls) == 2
    assert saved[key]["windows_completed"] == 4
    assert inserts == []


def test_later_window_sees_earlier_proposal_and_marks_overlap(monkeypatch):
    inserts, updates, _ = _setup(monkeypatch, _rows())
    calls = iter([
        ([{"name": "Apply a load balancer", "bloom_level": "apply"}], []),
        ([{"name": "Apply a load balancer configuration", "bloom_level": "apply"}], []),
        ([], []), ([], []),
    ])
    monkeypatch.setattr(skill_proposer, "_model", lambda _: next(calls))
    skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert len(inserts) == 1
    assert any("merged_count=2" in args[2].get("proposed_source", "")
               for args, kwargs in updates if args[0] == "skills")


def test_time_budget_guard_chains_without_starting_model_call(monkeypatch):
    inserts, updates, _ = _setup(monkeypatch, _rows())
    calls = []
    monkeypatch.setattr(skill_proposer, "_model", lambda _: calls.append(1) or ([], []))
    out = skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=40)
    assert out["remaining"] is True
    assert calls == [] and inserts == [] and updates == []


def test_last_seed_timestamp_only_after_all_modules_complete(monkeypatch):
    rows = _rows() + [{**_rows()[0], "id": "other", "module_ref": "m2"}]
    _, updates, saved = _setup(monkeypatch, rows)
    monkeypatch.setattr(skill_proposer, "_model", lambda _: ([], []))
    ticks = iter([0, 0, 0, 60, 60, 60])
    monkeypatch.setattr(skill_proposer.time, "monotonic", lambda: next(ticks))
    first = skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=60)
    assert first["remaining"] is True
    assert updates == []
    monkeypatch.setattr(skill_proposer.time, "monotonic", lambda: 0)
    skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert len(updates) == 1
    assert saved["proposal:c"]["status"] == "done"


def test_permanent_model_error_sets_failed_proposal_status(monkeypatch):
    from app.model_errors import ModelCallError
    _, _, saved = _setup(monkeypatch, _rows())
    monkeypatch.setattr(skill_proposer, "_model", lambda _: (_ for _ in ()).throw(ModelCallError(400, "invalid payload")))
    result = skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert result["stop_reason"] == "permanent_error"
    assert saved["proposal:c"]["status"] == "failed"


def test_bank_model_payload_and_proposal_parser(monkeypatch):
    class Response:
        is_success = True
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"skills":[{"name":"Apply subnetting","bloom_level":"apply","weight":1.2,"category":"subject"}]}'}}]}

    captured = {}
    class Client:
        def __init__(self, **kwargs): captured["timeout"] = kwargs["timeout"]
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, path, json, **kwargs): captured.update(json); return Response()

    monkeypatch.setattr(skill_proposer.httpx, "Client", Client)
    parsed, logistics = skill_proposer._model("source text")
    assert parsed == [{"name": "Apply subnetting", "bloom_level": "apply", "weight": 1.2}]
    assert logistics == []
    assert captured["model"] == "deepseek/deepseek-v4.1-flash:nitro"
    assert captured["max_completion_tokens"] == 8192
    assert captured["reasoning"] == {"max_tokens": 3072}
    assert captured["max_completion_tokens"] - captured["reasoning"]["max_tokens"] >= 5000
    assert captured["timeout"] == 45


def test_proposer_http_error_classes(monkeypatch):
    class Response:
        def __init__(self, status):
            self.status_code = status
            self.is_success = False
            self.text = '{"error":{"message":"bad request"}}'
        def json(self): return {"error": {"message": "bad request", "code": self.status_code}}

    class Client:
        status = 400
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response(self.status)

    client = Client()
    monkeypatch.setattr(skill_proposer.httpx, "Client", lambda **kwargs: client)
    monkeypatch.setattr(skill_proposer, "get_settings", lambda: type("S", (), {
        "openrouter_base_url": "https://example.invalid", "openrouter_api_key": "test",
        "openrouter_model_bank": "deepseek/deepseek-v4.1-flash:nitro",
    })())
    from app.model_errors import ModelCallError

    for status in (400, 401, 403, 404, 422):
        client.status = status
        try:
            skill_proposer._model("private source text")
        except ModelCallError as exc:
            assert (exc.permanent, exc.throttled, exc.transient) == (True, False, False)
            assert exc.status_code == status
        else:
            raise AssertionError(f"expected ModelCallError for status {status}")


def test_proposer_429_is_transient_throttle(monkeypatch):
    _mock_status(monkeypatch, 429)
    from app.model_errors import ModelCallError
    try:
        skill_proposer._model("private source text")
    except ModelCallError as exc:
        assert (exc.permanent, exc.throttled, exc.transient) == (False, True, True)
    else:
        raise AssertionError("expected 429 ModelCallError")


def test_proposer_5xx_is_transient(monkeypatch):
    _mock_status(monkeypatch, 503)
    from app.model_errors import ModelCallError
    try:
        skill_proposer._model("private source text")
    except ModelCallError as exc:
        assert (exc.permanent, exc.throttled, exc.transient) == (False, False, True)
    else:
        raise AssertionError("expected 5xx ModelCallError")


def test_within_window_near_duplicates_merge_and_log_dropped_name(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    inserts, _, _ = _setup(monkeypatch, _rows())
    monkeypatch.setattr(skill_proposer, "_model", lambda _: ([
        {"name": "Apply subnet routing", "bloom_level": "apply"},
        {"name": "Apply subnet routing rules", "bloom_level": "apply"},
    ], ["Certification pathway"]))
    skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert len(inserts) == 1
    assert "merged_count=2" in inserts[0]["proposed_source"]
    assert "name=Certification pathway reason=logistics" in caplog.text
    assert "reason=deduped" in caplog.text


def test_proposal_overlapping_approved_course_skill_is_dropped(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    approved = {"id": "approved-1", "name": "Existing approved skill",
                "status": "approved", "embedding": [1.0, 0.0],
                "created_at": "2025-01-01T00:00:00+00:00"}
    inserts, _, _ = _setup(monkeypatch, _rows(), existing=[approved])
    monkeypatch.setattr(skill_proposer, "_model", lambda _: ([
        {"name": "Apply the same approved skill", "bloom_level": "apply"}
    ], []))
    skill_proposer.run(course_id="c", institution_id="i", remaining_seconds=100)
    assert inserts == []
    assert "name=Apply the same approved skill reason=approved_overlap similarity=1.000" in caplog.text


def _mock_status(monkeypatch, status):
    class Response:
        status_code = status
        is_success = False
        text = '{"error":{"message":"temporary error"}}'
        def json(self): return {"error": {"message": "temporary error", "code": status}}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    monkeypatch.setattr(skill_proposer.httpx, "Client", Client)
    monkeypatch.setattr(skill_proposer, "get_settings", lambda: type("S", (), {
        "openrouter_base_url": "https://example.invalid", "openrouter_api_key": "test",
        "openrouter_model_bank": "deepseek/deepseek-v4.1-flash:nitro",
    })())
