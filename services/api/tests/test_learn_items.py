from app.learn import items as item_gen


def test_generate_question_persists_answer_key_and_returns_sanitized_view(monkeypatch) -> None:
    inserted = []
    requested_tasks = []
    request = {}

    monkeypatch.setattr(item_gen.rag, "retrieve", lambda **kwargs: [{"chunk_text": "Photosynthesis converts light to energy."}])
    monkeypatch.setattr(
        item_gen,
        "get_model_for",
        lambda task: requested_tasks.append(task) or "item-model",
    )
    monkeypatch.setattr(
        item_gen.bedrock,
        "converse",
        lambda **kwargs: request.update(kwargs) or (
            '{"prompt": "What does photosynthesis convert?", '
            '"choices": [{"id": "a", "label": "Light to chemical energy"}, {"id": "b", "label": "Chemical energy to light"}, {"id": "c", "label": "Heat to glucose"}, {"id": "d", "label": "Water to oxygen"}], '
            '"correct_choice_id": "a", "explanation": "Plants convert light into chemical energy."}'
        ),
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "item-1", **rows[0]}],
    )

    skill = {"id": "skill-1", "name": "Photosynthesis", "bloom_level": "understand"}
    result = item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=skill, kind="diagnostic",
    )

    assert result == {
        "id": "item-1",
        "skillId": "skill-1",
        "bloomLevel": "understand",
        "prompt": "What does photosynthesis convert?",
        "choices": [{"id": "a", "label": "Light to chemical energy"}, {"id": "b", "label": "Chemical energy to light"}, {"id": "c", "label": "Heat to glucose"}, {"id": "d", "label": "Water to oxygen"}],
    }
    assert "correct_choice_id" not in result
    assert inserted[0]["correct_choice_id"] == "a"
    assert requested_tasks == ["item"]
    assert request["response_format"] == item_gen._MCQ_RESPONSE_FORMAT


def test_generate_question_rejects_unusable_model_output_without_storing(monkeypatch) -> None:
    inserted = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen.bedrock, "converse", lambda **kwargs: "not json")
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "should-not-exist", **rows[0]}],
    )

    skill = {"id": "skill-2", "name": "Osmosis", "bloom_level": "remember"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected ItemGenerationError"
    except item_gen.ItemGenerationError:
        pass
    assert inserted == []


def test_generate_question_rejects_two_choice_output_without_storing(monkeypatch) -> None:
    inserted = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(
        item_gen.bedrock,
        "converse",
        lambda **kwargs: (
            '{"prompt": "Which statement best matches osmosis?", '
            '"choices": [{"id": "a", "label": "Water movement"}, {"id": "b", "label": "None"}], '
            '"correct_choice_id": "a", "explanation": ""}'
        ),
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "should-not-exist", **rows[0]}],
    )

    try:
        item_gen.generate_question(
            institution_id="inst-1",
            course_id="course-1",
            skill={"id": "skill-2", "name": "Osmosis"},
            kind="practice",
        )
        assert False, "expected ItemGenerationError"
    except item_gen.ItemGenerationError:
        pass
    assert inserted == []


def test_grade_compares_against_the_stored_answer_key_not_the_client(monkeypatch) -> None:
    monkeypatch.setattr(
        item_gen.db, "select",
        lambda table, params: [{
            "id": "item-1", "skill_id": "skill-1", "course_id": "course-1",
            "correct_choice_id": "a", "explanation": "because a",
        }],
    )

    right = item_gen.grade(institution_id="inst-1", item_id="item-1", choice_id="a")
    wrong = item_gen.grade(institution_id="inst-1", item_id="item-1", choice_id="b")

    assert right["correct"] is True
    assert wrong["correct"] is False
    assert right["skillId"] == "skill-1"


def test_grade_raises_when_item_is_missing_or_out_of_tenant(monkeypatch) -> None:
    monkeypatch.setattr(item_gen.db, "select", lambda table, params: [])

    try:
        item_gen.grade(institution_id="inst-1", item_id="missing", choice_id="a")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_weakest_skill_prefers_never_attempted_over_low_mastery(monkeypatch) -> None:
    def fake_select(table, params):
        if table == "skills":
            return [
                {"id": "skill-attempted", "name": "Attempted", "bloom_level": "apply"},
                {"id": "skill-new", "name": "Never attempted", "bloom_level": "apply"},
            ]
        if table == "mastery_state":
            return [{"skill_id": "skill-attempted", "estimate": 0.2}]
        raise AssertionError(f"unexpected table {table}")

    monkeypatch.setattr(item_gen.db, "select", fake_select)

    skill = item_gen.weakest_skill(institution_id="inst-1", user_id="user-1", course_id="course-1")

    assert skill["id"] == "skill-new"


def test_weakest_skill_returns_none_when_course_has_no_skills(monkeypatch) -> None:
    monkeypatch.setattr(item_gen.db, "select", lambda table, params: [])

    assert item_gen.weakest_skill(institution_id="inst-1", user_id="user-1", course_id="course-1") is None


def test_generate_question_threads_set_id_into_the_insert(monkeypatch) -> None:
    """A batched practice item must be persisted already grouped under its
    quiz_sets row, not patched afterward — so an item is never briefly
    persisted outside the set it was generated for."""
    inserted = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(
        item_gen.bedrock,
        "converse",
        lambda **kwargs: (
            '{"prompt": "Q?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, '
            '{"id": "c", "label": "C"}, {"id": "d", "label": "D"}], '
            '"correct_choice_id": "a", "explanation": "why"}'
        ),
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "item-1", **rows[0]}],
    )

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        set_id="set-9",
    )

    assert inserted[0]["set_id"] == "set-9"


def test_generate_question_omits_set_id_when_not_batched(monkeypatch) -> None:
    """Every pre-batch caller omits set_id and must keep producing exactly the
    same ungrouped row it always did — no phantom key in the insert."""
    inserted = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(
        item_gen.bedrock,
        "converse",
        lambda **kwargs: (
            '{"prompt": "Q?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, '
            '{"id": "c", "label": "C"}, {"id": "d", "label": "D"}], '
            '"correct_choice_id": "a", "explanation": "why"}'
        ),
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "item-1", **rows[0]}],
    )

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
    )

    assert "set_id" not in inserted[0]


# ---- bounded validation retry --------------------------------------------
# A model call can succeed at the HTTP level and still return an unusable body
# (malformed/truncated JSON, or a semantically wrong MCQ). bedrock.converse's
# own retry only covers transport/capability failures, so this second, narrow
# retry lives here — without it one bad roll in a 5-way POST /set batch 502s
# the whole set via map_concurrent's all-or-nothing propagation.

_VALID_MCQ = (
    '{"prompt": "Q?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, '
    '{"id": "c", "label": "C"}, {"id": "d", "label": "D"}], '
    '"correct_choice_id": "a", "explanation": "why"}'
)


def test_generate_question_retries_once_on_invalid_output_then_succeeds(monkeypatch) -> None:
    inserted = []
    calls = []

    def fake_converse(**kwargs):
        calls.append(kwargs)
        # First roll: unusable. Second roll: good.
        return "not json" if len(calls) == 1 else _VALID_MCQ

    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(item_gen.bedrock, "converse", fake_converse)
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "item-1", **rows[0]}],
    )

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    result = item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
    )

    assert result["id"] == "item-1"
    assert len(calls) == 2  # exactly one retry
    assert inserted[0]["correct_choice_id"] == "a"


def test_generate_question_gives_up_after_one_retry(monkeypatch) -> None:
    """A model that fails twice is a real signal — do not loop. Exactly two
    attempts, then ItemGenerationError, and nothing persisted."""
    inserted = []
    calls = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(
        item_gen.bedrock, "converse",
        lambda **kwargs: calls.append(kwargs) or "not json",
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: inserted.extend(rows) or [{"id": "x", **rows[0]}],
    )

    skill = {"id": "skill-2", "name": "Osmosis", "bloom_level": "remember"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected ItemGenerationError"
    except item_gen.ItemGenerationError:
        pass

    assert len(calls) == 2
    assert inserted == []


def test_generate_question_does_not_retry_a_first_try_success(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(
        item_gen.bedrock, "converse",
        lambda **kwargs: calls.append(kwargs) or _VALID_MCQ,
    )
    monkeypatch.setattr(
        item_gen.db, "insert",
        lambda table, rows: [{"id": "item-1", **rows[0]}],
    )

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
    )

    assert len(calls) == 1  # no wasted second call when the first is good


def test_generate_question_does_not_retry_a_provider_outage(monkeypatch) -> None:
    """A provider failure (429/5xx/retired model) is NOT a validation failure:
    bedrock.converse already gave it one cross-provider fallback attempt, so
    retrying it again here would just hammer the same rate limit. Exactly one
    attempt, then surface."""
    calls = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")

    def boom(**kwargs):
        calls.append(kwargs)
        raise item_gen.ModelUnavailableError(
            "provider busy", provider="openrouter", model_id="m", status_code=429,
        )

    monkeypatch.setattr(item_gen.bedrock, "converse", boom)

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected ItemGenerationError"
    except item_gen.ItemGenerationError:
        pass

    assert len(calls) == 1  # no second roll on a provider outage


def test_generate_question_still_retries_a_validation_failure(monkeypatch) -> None:
    """The validation retry is unchanged for the failure it was written for:
    a body that arrived but was unusable."""
    calls = []
    monkeypatch.setattr(item_gen.rag, "retrieve",
                    lambda **kwargs: [{"chunk_text": "Managed AWS services trade higher per-unit cost for reduced operational overhead; self-managed alternatives trade lower cost for more control and operational responsibility."}])
    monkeypatch.setattr(item_gen, "get_model_for", lambda task: "item-model")
    monkeypatch.setattr(
        item_gen.bedrock, "converse",
        lambda **kwargs: calls.append(kwargs) or "not json",
    )

    skill = {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected ItemGenerationError"
    except item_gen.ItemGenerationError:
        pass

    assert len(calls) == 2  # validation failure DOES get its one retry


# ---- the no-content guard -------------------------------------------------
# This is the fix for the "plausible but meaningless questions" failure. With
# an empty retrieval the module used to fall back to the skill name as the
# excerpt, so the model wrote a stem by rewording the skill name, made the
# skill's own phrase the answer every time, and invented nonsense distractors.
# Everything passed schema validation, so nothing flagged it. Now it refuses.


def test_generate_question_refuses_when_skill_has_no_content(monkeypatch) -> None:
    monkeypatch.setattr(item_gen.rag, "retrieve", lambda **kwargs: [])
    # If the guard fails, this would be reached and used to fabricate a question.
    monkeypatch.setattr(
        item_gen.bedrock, "converse",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("must not call the model without grounded content")
        ),
    )

    skill = {"id": "skill-1", "name": "Compare managed AWS services", "bloom_level": "evaluate"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected NoCourseContentError"
    except item_gen.NoCourseContentError as exc:
        # The message names the missing prerequisite, not the model.
        assert "no course material" in str(exc).lower()
        assert exc.skill_name == "Compare managed AWS services"


def test_no_content_error_is_an_item_generation_error(monkeypatch) -> None:
    """It must still map to the existing 502 handler, so routers that do not
    catch the narrower type keep working."""
    err = item_gen.NoCourseContentError(skill_name="X")
    assert isinstance(err, item_gen.ItemGenerationError)


def test_generate_question_refuses_when_chunks_are_blank(monkeypatch) -> None:
    """Retrieval can return rows whose text is empty/whitespace. Those are as
    ungrounded as no rows at all, so they must not sneak past the guard."""
    monkeypatch.setattr(
        item_gen.rag, "retrieve",
        lambda **kwargs: [{"chunk_text": "   "}, {"chunk_text": ""}],
    )
    skill = {"id": "skill-1", "name": "Osmosis", "bloom_level": "remember"}
    try:
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=skill, kind="practice",
        )
        assert False, "expected NoCourseContentError"
    except item_gen.NoCourseContentError:
        pass
