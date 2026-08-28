"""Guided lesson tests. Focus on the contract that matters: generate-once
idempotency, outline validation with a never-empty fallback, and that a
generated step carries structured content plus a server-graded check item."""
from app.learn import lessons


def test_get_or_generate_returns_stored_lesson_without_regenerating(monkeypatch):
    """If a ready lesson exists, load it and never call the model."""
    called = {"converse": 0}
    monkeypatch.setattr(lessons.bedrock, "converse",
                        lambda **kw: called.__setitem__("converse", called["converse"] + 1) or "{}")

    def fake_select(table, params):
        if table == "guided_lessons":
            return [{"id": "lesson-1", "status": "ready", "skill_id": "s-1",
                     "module_ref": None, "title": "Skill One"}]
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "sum",
                     "detail_points": [], "misconception": None, "key_takeaway": None,
                     "bloom_level": "understand", "check_item_id": None}]
        return []

    monkeypatch.setattr(lessons.db, "select", fake_select)

    lesson = lessons.get_or_generate_lesson(
        institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill One"},
    )
    assert lesson["lessonId"] == "lesson-1"
    assert lesson["steps"][0]["summary"] == "sum"
    assert called["converse"] == 0  # replay, not regenerate


def test_outline_validation_keeps_valid_steps_and_defaults_bloom():
    raw = """{"steps": [
        {"title": "Recall the definition", "focus": "what it is", "bloom_level": "remember"},
        {"title": "", "focus": "skip me", "bloom_level": "apply"},
        {"title": "Apply it", "focus": "use it", "bloom_level": "not-a-bloom"}
    ]}"""
    # Drive _generate_outline through a stubbed model call.
    import app.learn.lessons as L
    orig = L.bedrock.converse
    try:
        L.bedrock.converse = lambda **kw: raw
        out = L._generate_outline(
            skill={"id": "s-1", "name": "S", "bloom_level": "understand"}, context="ctx",
        )
    finally:
        L.bedrock.converse = orig
    titles = [s["title"] for s in out]
    assert titles == ["Recall the definition", "Apply it"]  # empty-title dropped
    assert out[1]["bloom_level"] == "understand"  # invalid bloom fell back to skill's


def test_outline_falls_back_to_single_step_on_garbage(monkeypatch):
    monkeypatch.setattr(lessons.bedrock, "converse", lambda **kw: "not json")
    out = lessons._generate_outline(
        skill={"id": "s-1", "name": "Boolean logic", "bloom_level": "apply"}, context="ctx",
    )
    assert len(out) == 1
    assert out[0]["title"] == "Boolean logic"  # never empty


def test_step_content_falls_back_cleanly(monkeypatch):
    monkeypatch.setattr(lessons.bedrock, "converse", lambda **kw: "not json")
    content = lessons._generate_step_content(
        skill={"id": "s-1", "name": "S"},
        step={"title": "T", "focus": "the focus"}, context="ctx",
    )
    assert content["summary"] == "the focus"
    assert content["detail_points"] == []
    assert content["misconception"] is None


def test_generation_persists_steps_in_position_order_even_when_parallel_completion_is_out_of_order(monkeypatch):
    """The risky part of parallelizing per-step generation: content is built
    concurrently (so steps can finish in any order), but they must still be
    INSERTED with position matching their place in the outline, not their
    completion order."""
    import time

    inserted_positions = []

    monkeypatch.setattr(lessons, "_context_for", lambda **kw: ("ctx", []))
    monkeypatch.setattr(lessons, "_generate_outline", lambda **kw: [
        {"title": f"Step {i}", "focus": f"focus {i}", "bloom_level": "understand"}
        for i in range(4)
    ])

    def content_with_variable_delay(*, skill, step, context):
        # Step 0 is slowest, step 3 is fastest — completion order is the
        # REVERSE of outline order, the worst case for the bug this guards.
        idx = int(step["title"].split()[-1])
        time.sleep(0.02 * (4 - idx))
        return {"summary": step["focus"], "detail_points": [], "misconception": None,
                "key_takeaway": None}

    monkeypatch.setattr(lessons, "_generate_step_content", content_with_variable_delay)
    monkeypatch.setattr(lessons.item_gen, "generate_question", lambda **kw: {"id": "check"})

    def fake_insert(table, rows, prefer="return=representation"):
        if table == "guided_lesson_steps":
            inserted_positions.append((rows[0]["position"], rows[0]["summary"]))
        return []

    monkeypatch.setattr(lessons.db, "insert", fake_insert)

    lessons._generate_steps_into(
        institution_id="inst-1", course_id="c-1",
        skill={"id": "s-1", "name": "Skill"}, lesson_id="lesson-1",
    )

    assert inserted_positions == [
        (0, "focus 0"), (1, "focus 1"), (2, "focus 2"), (3, "focus 3"),
    ]


def test_generation_persists_steps_and_wires_check_item(monkeypatch):
    """First open: outline -> per-step content + a check MCQ, all persisted,
    lesson flipped to ready."""
    inserts = {"guided_lessons": [], "guided_lesson_steps": []}
    updates = []

    monkeypatch.setattr(lessons, "_context_for", lambda **kw: ("grounded context", ["chunk-1"]))
    monkeypatch.setattr(lessons, "_generate_outline", lambda **kw: [
        {"title": "Step A", "focus": "focus a", "bloom_level": "understand"},
    ])
    monkeypatch.setattr(lessons, "_generate_step_content", lambda **kw: {
        "summary": "explained", "detail_points": ["p1", "p2"],
        "misconception": "a myth", "key_takeaway": "the point",
    })
    monkeypatch.setattr(lessons.item_gen, "generate_question",
                        lambda **kw: {"id": "check-1", "prompt": "Q?", "choices": []})

    def fake_select(table, params):
        if table == "guided_lessons":
            # Existence check (select id,status) sees nothing -> generate.
            # load_lesson's read (which asks for skill_id/title) sees the
            # row the generation just inserted.
            if "skill_id" in params.get("select", ""):
                return [{"id": "lesson-1", "status": "ready", "skill_id": "s-1",
                         "module_ref": "Module 1", "title": "Skill"}]
            return []
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "explained",
                     "detail_points": ["p1", "p2"], "misconception": "a myth",
                     "key_takeaway": "the point", "bloom_level": "understand",
                     "check_item_id": "check-1"}]
        if table == "generated_items":
            return [{"id": "check-1", "prompt": "Q?", "choices": [{"id": "a", "label": "x"}]}]
        return []

    def fake_insert(table, rows, prefer="return=representation"):
        inserts.setdefault(table, []).extend(rows)
        return [{"id": "lesson-1", **rows[0]}] if table == "guided_lessons" else []

    monkeypatch.setattr(lessons.db, "select", fake_select)
    monkeypatch.setattr(lessons.db, "insert", fake_insert)
    monkeypatch.setattr(lessons.db, "update", lambda table, filters, values: updates.append(values) or [])

    lesson = lessons.get_or_generate_lesson(
        institution_id="inst-1", course_id="c-1",
        skill={"id": "s-1", "name": "Skill", "bloom_level": "understand", "module_ref": "Module 1"},
    )

    assert len(inserts["guided_lessons"]) == 1
    assert inserts["guided_lessons"][0]["status"] == "generating"
    assert len(inserts["guided_lesson_steps"]) == 1
    assert inserts["guided_lesson_steps"][0]["check_item_id"] == "check-1"
    assert updates and updates[0]["status"] == "ready"
    # Client view carries the check WITHOUT an answer key.
    assert lesson["steps"][0]["check"]["itemId"] == "check-1"
    assert "correct_choice_id" not in lesson["steps"][0]["check"]
