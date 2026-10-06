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


def test_only_is_not_absolute_but_no_value_and_identical_are():
    for phrase in (
        "The badge is only for internal use and has no value to employers.",
        "The badge is awarded only after passing the AWS Certified Cloud Practitioner exam.",
        "It is suitable only for students who already have AWS certifications.",
    ):
        item = _item()
        item["choices"][1]["label"] = phrase
        item["choices"][2]["label"] = "A different valid alternative"
        assert bank_build._valid_items([item], [])

    for phrase in ("It has no value here", "It has identical behavior"):
        item = _item()
        item["choices"][1]["label"] = phrase
        item["choices"][2]["label"] = "It always works"
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


def test_pending_excludes_leased_backoff_no_material_and_failed_skill():
    now = bank_build._iso(bank_build._now())
    rows = [
        {"skill_id": "eligible", "status": "building", "depth": 1, "mcq_ready": 0, "mcq_target": 5},
        {"skill_id": "leased", "status": "building", "depth": 1, "mcq_ready": 0, "mcq_target": 5,
         "leased_until": bank_build._iso(bank_build._now() + bank_build.timedelta(minutes=5))},
        {"skill_id": "backoff", "status": "building", "depth": 1, "mcq_ready": 0, "mcq_target": 5,
         "next_attempt_at": bank_build._iso(bank_build._now() + bank_build.timedelta(minutes=5))},
        {"skill_id": "no-material", "status": "no_material", "depth": 1, "mcq_ready": 0, "mcq_target": 5},
        {"skill_id": "failed-this-run", "status": "building", "depth": 1, "mcq_ready": 0, "mcq_target": 5},
    ]
    assert now
    assert [row["skill_id"] for row in bank_build._pending(rows, excluded_skill_ids={"failed-this-run"})] == ["eligible"]


def test_only_backoff_skills_are_not_remaining():
    rows = [{"skill_id": "backoff", "status": "building", "depth": 1, "mcq_ready": 0, "mcq_target": 5,
             "next_attempt_at": bank_build._iso(bank_build._now() + bank_build.timedelta(minutes=5))}]
    assert bank_build._pending(rows) == []


def test_scheduled_run_includes_serving_and_non_serving_courses(monkeypatch):
    course_query = []
    courses = [
        {"id": "serving-course", "institution_id": "institution-1", "bank_serving": True},
        {"id": "legacy-course", "institution_id": "institution-1", "bank_serving": False},
    ]

    def select(table, params):
        if table == "courses":
            course_query.append(params)
            return courses
        return []

    monkeypatch.setattr(bank_build.db, "select", select)
    monkeypatch.setattr(bank_build.db, "upsert", lambda *args, **kwargs: [])
    monkeypatch.setattr(bank_build.db, "update", lambda *args, **kwargs: [])
    result = bank_build.run()

    assert result["courses"] == 2
    assert "bank_serving" not in course_query[0]


def test_serving_course_replenishment_runs_on_scheduled_build(monkeypatch):
    replenished = []

    def select(table, params):
        if table == "courses":
            return [{"id": "serving-course", "institution_id": "institution-1", "bank_serving": True}]
        return []

    monkeypatch.setattr(bank_build.db, "select", select)
    monkeypatch.setattr(bank_build, "_replenish_context", lambda course_id: replenished.append(course_id) or {"active": {}, "seen": {}, "live_counts": {}})
    monkeypatch.setattr(bank_build.db, "upsert", lambda *args, **kwargs: [])
    monkeypatch.setattr(bank_build.db, "update", lambda *args, **kwargs: [])
    bank_build.run()

    assert replenished == ["serving-course"]


def test_serving_backoff_resumes_on_first_run_after_next_attempt():
    past = bank_build._iso(bank_build._now() - bank_build.timedelta(seconds=1))
    future = bank_build._iso(bank_build._now() + bank_build.timedelta(minutes=5))
    state = {"skill_id": "serving-skill", "status": "building", "depth": 1,
             "mcq_ready": 4, "mcq_target": 5, "next_attempt_at": past}
    assert bank_build._pending([state]) == [state]
    state["next_attempt_at"] = future
    assert bank_build._pending([state]) == []


def test_targeted_run_queries_and_touches_exactly_one_course(monkeypatch):
    requested = "course-requested"
    queried = []

    def select(table, params):
        if table == "courses":
            queried.append(params)
            assert params["id"] == f"eq.{requested}"
            return [{"id": requested, "institution_id": "institution-1"}]
        if table in {"skills", "skill_bank_state", "enrollments", "evidence_events",
                     "item_exposures", "generated_items", "content_items"}:
            return []
        raise AssertionError(f"unexpected select: {table}")

    monkeypatch.setattr(bank_build.db, "select", select)
    monkeypatch.setattr(bank_build.db, "upsert", lambda *args, **kwargs: [])
    monkeypatch.setattr(bank_build.db, "update", lambda *args, **kwargs: [])
    result = bank_build.run(course_id=requested)
    assert result["courses"] == 1
    assert len(queried) == 1


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


def test_depth_reuses_stored_skill_embedding_without_embedding_call(monkeypatch):
    captured = {}
    monkeypatch.setattr(bank_build.rag, "retrieve_embedding",
                        lambda **kwargs: captured.update(kwargs) or [])
    monkeypatch.setattr(bank_build.rag.embed, "embed",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("embedding call")))
    depth, chunks = bank_build._depth(
        {"embedding": "[1.0,0.0]"}, "institution", "course",
    )
    assert depth == 0
    assert chunks == []
    assert captured["query_embedding"] == [1.0, 0.0]


def test_new_or_retagged_content_triggers_recompute():
    assert bank_build._needs_depth_recompute(None, [])
    assert bank_build._content_changed(
        [{"created_at": "2026-10-06T10:00:00+00:00", "tag_attempted_at": None}],
        "2026-10-06T09:00:00+00:00",
    )
    assert bank_build._content_changed(
        [{"created_at": "2026-10-06T08:00:00+00:00", "tag_attempted_at": "2026-10-06T10:00:01+00:00"}],
        "2026-10-06T09:00:00+00:00",
    )
    assert not bank_build._content_changed(
        [{"created_at": "2026-10-06T08:00:00+00:00", "tag_attempted_at": "2026-10-06T08:30:00+00:00"}],
        "2026-10-06T09:00:00+00:00",
    )


def test_replenish_context_matches_per_skill_decision():
    context = {
        "active": {"skill": {"student"}},
        "seen": {("student", "skill"): {str(i) for i in range(11)}},
        "live_counts": {"skill": 20},
    }
    # The old per-skill implementation raises by one step when nine of the
    # twenty bank items have been tested, leaving fewer than LOW_WATER unseen.
    assert bank_build._target_from_context("skill", 4,
                                          {"mcq_target": 20}, context) == 24


def test_failure_counter_increments_once(monkeypatch):
    updates = []
    monkeypatch.setattr(bank_build.db, "update", lambda table, filters, values: updates.append(values) or [])
    state = {"course_id": "c", "skill_id": "s", "consecutive_failures": 1}
    bank_build._record_failure(state, RuntimeError("failed"))
    assert updates[0]["consecutive_failures"] == 2


def test_duplicate_saturation_triggers_after_two_zero_valid_batches(monkeypatch):
    updates = []
    monkeypatch.setattr(bank_build.db, "update", lambda table, filters, values: updates.append(values) or [])
    duplicate_counts = {key: 0 for key in bank_build._REJECTION_KEYS}
    duplicate_counts.update(duplicate_hash=3, near_duplicate=1, reused_choice_set=1)
    state = {"course_id": "c", "skill_id": "s", "depth": 4, "mcq_ready": 11,
             "mcq_target": 20, "consecutive_failures": 0}
    assert not bank_build._record_failure(state, bank_build.ZeroValidBatchError(duplicate_counts), duplicate_counts)
    assert state["consecutive_failures"] == 1
    assert bank_build._record_failure(state, bank_build.ZeroValidBatchError(duplicate_counts), duplicate_counts)
    assert state["status"] == "ready"
    assert state["mcq_target"] == 11
    assert state["saturated_depth"] == 4
    assert state["next_attempt_at"] is None
    assert state["last_error"] is None
    assert updates[-1]["saturated_at"]


def test_non_duplicate_zero_valid_batches_keep_backoff(monkeypatch):
    updates = []
    monkeypatch.setattr(bank_build.db, "update", lambda table, filters, values: updates.append(values) or [])
    counts = {key: 0 for key in bank_build._REJECTION_KEYS}
    counts["schema"] = 5
    state = {"course_id": "c", "skill_id": "s", "depth": 4, "mcq_ready": 11,
             "mcq_target": 20, "consecutive_failures": 0}
    bank_build._record_failure(state, bank_build.ZeroValidBatchError(counts), counts)
    bank_build._record_failure(state, bank_build.ZeroValidBatchError(counts), counts)
    assert state["status"] == "building"
    assert state["consecutive_failures"] == 2
    assert state["next_attempt_at"]
    assert "saturated_at" not in updates[-1]


def test_saturation_blocks_replenishment_and_depth_change_clears_it():
    context = {"active": {"s": {"student"}}, "seen": {("student", "s"): set()}, "live_counts": {"s": 11}}
    saturated = {"mcq_ready": 11, "mcq_target": 26, "saturated_at": "now", "saturated_depth": 4}
    assert bank_build._target_from_context("s", 4, saturated, context) == 11
    assert bank_build._target_from_context("s", 5, saturated, context) == 26


def test_bank_model_log_includes_course_and_skill(caplog):
    with caplog.at_level("INFO", logger="kala.worker.bank"):
        bank_build._log_model_call({"course_id": "course", "skill_id": "skill", "model": "m",
                                    "provider": "p", "latency_ms": 1, "finish_reason": "stop",
                                    "prompt_tokens": 1, "completion_tokens": 1, "reasoning_tokens": 0,
                                    "reasoning_chars": 0, "usage_keys": "", "cost": 0})
    assert "course_id=course" in caplog.text
    assert "skill_id=skill" in caplog.text


def test_non_stop_finish_is_failure(monkeypatch):
    captured = {}
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
        def post(self, *args, **kwargs):
            captured.update(kwargs)
            return Response()
    monkeypatch.setattr(bank_build.httpx, "Client", Client)
    monkeypatch.setattr(bank_build, "get_settings", lambda: type("S", (), {"openrouter_model_bank": "m", "bank_reasoning_effort": "low", "bank_reasoning_max_tokens": 3072, "openrouter_base_url": "https://x", "openrouter_api_key": "k"})())
    try:
        bank_build._call_model(skill={"name": "x"}, context="x", do_not_repeat=[], remaining=50)
    except RuntimeError as exc:
        assert "non-stop" in str(exc)
    else:
        raise AssertionError("non-stop response must fail")
    assert captured["json"]["reasoning"] == {"max_tokens": 3072}
