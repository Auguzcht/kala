"""Tests for the guided-lesson reclaim path (Learn Loop v2 review fixes).

Covers the three failure modes the initial version could hit:
  1. two concurrent first-opens racing the INSERT (409 from PostgREST)
  2. a lesson stuck at status='generating' from a prior crashed attempt
  3. a lesson at status='failed' from a prior exception

In every case the fix must (a) never leave the row permanently un-completable
and (b) never duplicate step rows via stale positions from a partial attempt.
"""
import httpx

from app.learn import lessons


def _resp(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://example.test/guided_lessons")
    return httpx.Response(status_code=status_code, request=request)


def _stub_generation(monkeypatch, *, raise_on_step: bool = False):
    monkeypatch.setattr(lessons, "_context_for", lambda **kw: ("ctx", ["chunk-1"]))
    monkeypatch.setattr(lessons, "_generate_outline", lambda **kw: [
        {"title": "Step A", "focus": "focus a", "bloom_level": "understand"},
    ])
    if raise_on_step:
        def boom(**kw):
            raise RuntimeError("model exploded mid-step")
        monkeypatch.setattr(lessons, "_generate_step_content", boom)
    else:
        monkeypatch.setattr(lessons, "_generate_step_content", lambda **kw: {
            "summary": "explained", "detail_points": [], "misconception": None,
            "key_takeaway": None,
        })
    monkeypatch.setattr(lessons.item_gen, "generate_question",
                        lambda **kw: {"id": "check-1", "prompt": "Q?", "choices": []})


def test_stuck_generating_lesson_is_reclaimed_not_served_incomplete(monkeypatch):
    """A lesson stuck at 'generating' (e.g. a crashed prior attempt) must be
    regenerated on the next open, not returned as-is and not left stuck."""
    deleted = []
    updates = []
    _stub_generation(monkeypatch)

    def fake_select(table, params):
        if table == "guided_lessons":
            # First lookup finds the stuck row; final load_lesson call needs
            # the full row shape.
            if params.get("select") == "id,status":
                return [{"id": "lesson-1", "status": "generating"}]
            return [{"id": "lesson-1", "status": "ready", "skill_id": "s-1",
                     "module_ref": None, "title": "Skill"}]
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "explained",
                     "detail_points": [], "misconception": None, "key_takeaway": None,
                     "bloom_level": "understand", "check_item_id": "check-1"}]
        if table == "generated_items":
            return [{"id": "check-1", "prompt": "Q?", "choices": []}]
        return []

    monkeypatch.setattr(lessons.db, "select", fake_select)
    monkeypatch.setattr(lessons.db, "delete", lambda table, filters: deleted.append((table, filters)))
    monkeypatch.setattr(lessons.db, "insert", lambda table, rows, prefer="return=representation": [])
    monkeypatch.setattr(lessons.db, "update",
                        lambda table, filters, values: updates.append(values) or [])

    result = lessons.get_or_generate_lesson(
        institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill"},
    )

    assert deleted == [("guided_lesson_steps", {"lesson_id": "eq.lesson-1"})]
    assert {"status": "generating"} in updates   # reclaimed
    assert {"status": "ready"} in updates        # completed after regeneration
    assert result["lessonId"] == "lesson-1"


def test_failed_lesson_is_retried_on_next_open(monkeypatch):
    """A lesson at status='failed' takes the same reclaim path as 'generating'."""
    updates = []
    _stub_generation(monkeypatch)

    def fake_select(table, params):
        if table == "guided_lessons":
            if params.get("select") == "id,status":
                return [{"id": "lesson-1", "status": "failed"}]
            return [{"id": "lesson-1", "status": "ready", "skill_id": "s-1",
                     "module_ref": None, "title": "Skill"}]
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "explained",
                     "detail_points": [], "misconception": None, "key_takeaway": None,
                     "bloom_level": "understand", "check_item_id": "check-1"}]
        if table == "generated_items":
            return [{"id": "check-1", "prompt": "Q?", "choices": []}]
        return []

    monkeypatch.setattr(lessons.db, "select", fake_select)
    monkeypatch.setattr(lessons.db, "delete", lambda table, filters: None)
    monkeypatch.setattr(lessons.db, "insert", lambda table, rows, prefer="return=representation": [])
    monkeypatch.setattr(lessons.db, "update",
                        lambda table, filters, values: updates.append(values) or [])

    result = lessons.get_or_generate_lesson(
        institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill"},
    )
    assert {"status": "ready"} in updates
    assert result["status"] == "ready"


def test_exception_during_generation_marks_failed_and_reraises(monkeypatch):
    """A model/DB error mid-loop must mark the row 'failed', not leave it at
    'generating' forever, and the error must still propagate to the caller."""
    updates = []
    _stub_generation(monkeypatch, raise_on_step=True)

    def fake_select(table, params):
        if table == "guided_lessons" and params.get("select") == "id,status":
            return []  # none yet -> fresh insert
        return []

    monkeypatch.setattr(lessons.db, "select", fake_select)
    monkeypatch.setattr(
        lessons.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "lesson-1", **rows[0]}],
    )
    monkeypatch.setattr(lessons.db, "update",
                        lambda table, filters, values: updates.append(values) or [])

    try:
        lessons.get_or_generate_lesson(
            institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill"},
        )
        assert False, "expected the RuntimeError to propagate"
    except RuntimeError:
        pass

    assert {"status": "failed"} in updates
    assert {"status": "ready"} not in updates


def test_concurrent_insert_conflict_is_treated_as_found_not_an_error(monkeypatch):
    """Two requests race to create the shell. The loser's INSERT gets a 409
    from PostgREST (unique_violation on course_id, skill_id); that must be
    caught and treated the same as finding an existing row, not surfaced as a
    server error."""
    updates = []
    _stub_generation(monkeypatch)
    select_calls = {"n": 0}

    def fake_select(table, params):
        if table == "guided_lessons" and params.get("select") == "id,status":
            select_calls["n"] += 1
            if select_calls["n"] == 1:
                return []  # initial lookup: nothing yet, so we attempt insert
            return [{"id": "lesson-1", "status": "generating"}]  # re-fetch after 409
        if table == "guided_lessons":
            return [{"id": "lesson-1", "status": "ready", "skill_id": "s-1",
                     "module_ref": None, "title": "Skill"}]
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "explained",
                     "detail_points": [], "misconception": None, "key_takeaway": None,
                     "bloom_level": "understand", "check_item_id": "check-1"}]
        if table == "generated_items":
            return [{"id": "check-1", "prompt": "Q?", "choices": []}]
        return []

    def fake_insert(table, rows, prefer="return=representation"):
        if table == "guided_lessons":
            raise httpx.HTTPStatusError("conflict", request=None, response=_resp(409))
        return []

    monkeypatch.setattr(lessons.db, "select", fake_select)
    monkeypatch.setattr(lessons.db, "insert", fake_insert)
    monkeypatch.setattr(lessons.db, "delete", lambda table, filters: None)
    monkeypatch.setattr(lessons.db, "update",
                        lambda table, filters, values: updates.append(values) or [])

    result = lessons.get_or_generate_lesson(
        institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill"},
    )
    assert result["lessonId"] == "lesson-1"
    assert {"status": "ready"} in updates  # recovered and completed, no 500


def test_non_conflict_insert_error_still_propagates(monkeypatch):
    """A genuine server error (not a 409 race) must not be swallowed."""
    monkeypatch.setattr(lessons, "_context_for", lambda **kw: ("ctx", []))
    monkeypatch.setattr(lessons.db, "select", lambda table, params: [])
    monkeypatch.setattr(
        lessons.db, "insert",
        lambda table, rows, prefer="return=representation": (_ for _ in ()).throw(
            httpx.HTTPStatusError("server error", request=None, response=_resp(500))
        ),
    )
    try:
        lessons.get_or_generate_lesson(
            institution_id="inst-1", course_id="c-1", skill={"id": "s-1", "name": "Skill"},
        )
        assert False, "expected the 500 to propagate"
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 500
