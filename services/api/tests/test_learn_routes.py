import itertools
import threading
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.learn.items import ItemGenerationError
from app.main import app
from app.routers import flashcards, practice


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="user-1", institution_id="institution-1", app_role="student")


def test_practice_next_returns_none_when_course_has_no_skills(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.item_gen, "weakest_skill", lambda **kwargs: None)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "course-1", "item": None}


def test_practice_next_generates_an_item_for_the_weakest_skill(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: {"id": "item-1", "skillId": "skill-1", "bloomLevel": "apply",
                          "prompt": "...", "choices": []},
    )

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["id"] == "item-1"


def test_practice_next_returns_safe_502_when_generation_is_invalid(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.item_gen,
        "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )

    def raise_invalid(**kwargs):
        raise ItemGenerationError("Kala could not create a valid question. Please try again.")

    monkeypatch.setattr(practice.item_gen, "generate_question", raise_invalid)
    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Kala could not create a valid question. Please try again.",
    }


def test_practice_submit_writes_evidence_and_updates_the_tracer(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_rows = []
    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1", "correct": True, "explanation": "why"},
    )
    monkeypatch.setattr(practice.db, "insert_evidence", lambda rows: evidence_rows.extend(rows) or rows)
    monkeypatch.setattr(practice.tracer, "apply_evidence", lambda **kwargs: {"estimate": 0.65})

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/submit",
                json={"item_id": "item-1", "choice_id": "a", "latency_ms": 1200},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"correct": True, "explanation": "why", "mastery": 0.65}
    assert evidence_rows[0]["type"] == "practice"
    assert evidence_rows[0]["correct"] is True


def test_practice_submit_404s_on_unknown_item(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user

    def raise_missing(**kwargs):
        raise ValueError("item not found")

    monkeypatch.setattr(practice.item_gen, "grade", raise_missing)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/submit",
                json={"item_id": "missing", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_flashcards_deck_seeds_new_cards_when_nothing_is_due(monkeypatch) -> None:
    """With no due cards yet, the deck tops up with a fresh card per
    untracked skill, marks it 'new', and returns the flip back (answer label
    + explanation). Study mode is a flip, not an MCQ: `choices` is NOT part of
    the payload, and the raw answer key never appears."""
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "skills":
            return [{"id": "skill-1", "name": "Recursion", "bloom_level": "apply",
                     "module_ref": "Module 1"}]
        if table == "srs_state":  # nothing tracked yet
            return []
        if table == "generated_items":  # the back-derivation query
            return [{"id": "card-1", "correct_choice_id": "a", "explanation": "a function calling itself",
                     "choices": [{"id": "a", "label": "self-reference"},
                                 {"id": "b", "label": "a loop"}]}]
        return []

    monkeypatch.setattr(flashcards.db, "select", fake_select)
    monkeypatch.setattr(flashcards.srs, "due_cards", lambda **kwargs: [])
    monkeypatch.setattr(flashcards.srs, "ensure_tracked", lambda **kwargs: None)
    monkeypatch.setattr(flashcards.srs, "stats",
                        lambda **kwargs: {"tracked": 0, "due": 0, "learning": 0, "mastered": 0})
    monkeypatch.setattr(
        flashcards.item_gen, "generate_question",
        lambda **kwargs: {"id": "card-1", "skillId": "skill-1", "bloomLevel": "apply",
                          "prompt": "What is recursion?",
                          "choices": [{"id": "a", "label": "self-reference"},
                                      {"id": "b", "label": "a loop"}]},
    )

    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/course-1/deck")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["courseId"] == "course-1"
    assert len(body["cards"]) == 1
    card = body["cards"][0]
    assert card["itemId"] == "card-1"
    assert card["state"] == "new"
    assert card["back"] == {"label": "self-reference", "explanation": "a function calling itself"}
    # Study mode is a flip: no choices, and never the raw answer key.
    assert "choices" not in card
    assert "correct_choice_id" not in card
    assert body["stats"]["due"] == 0


def test_flashcards_review_is_a_self_mark_that_never_moves_the_twin(monkeypatch) -> None:
    """Study mode is not assessment. Review writes a flashcard evidence_event
    (correct=remembered, so the research export still sees study behavior) and
    advances the spaced-repetition schedule, but NEVER calls the tracer —
    mastery must not move on a self-report."""
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_rows = []
    srs_calls = []

    monkeypatch.setattr(
        flashcards.db, "select",
        lambda table, params: [{"id": "card-1", "skill_id": "skill-1"}],
    )
    monkeypatch.setattr(flashcards.db, "insert_evidence", lambda rows: evidence_rows.extend(rows) or rows)
    # The module must not even import the tracer any more — that is the
    # strongest form of "study never moves mastery": there is no code path
    # that could call it, not merely a path that happens not to.
    assert not hasattr(flashcards, "tracer")
    monkeypatch.setattr(
        flashcards.srs, "review",
        lambda **kwargs: srs_calls.append(kwargs) or SimpleNamespace(
            graduated=False, interval_hours=4.0, box=0,
        ),
    )
    monkeypatch.setattr(
        flashcards.xp, "summary",
        lambda **kwargs: {"xp": 12, "streakDays": 1, "badges": [], "attempts": 6, "correct": 3},
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/review",
                json={"item_id": "card-1", "remembered": False, "latency_ms": 900},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["remembered"] is False
    assert body["graduated"] is False
    assert body["dueInHours"] == 4.0
    assert body["reward"]["xp"] == 12
    # No `correct`/`mastery` in the response — study does not grade.
    assert "correct" not in body
    assert "mastery" not in body
    # The research-visible evidence row is written with the self-mark...
    assert evidence_rows[0]["type"] == "flashcard"
    assert evidence_rows[0]["correct"] is False
    assert evidence_rows[0]["latency_ms"] == 900
    # ...the schedule advances on the self-mark...
    assert srs_calls[0]["correct"] is False
    # ...and the twin is never touched (no tracer import exists to call).


# ---- POST /practice/{course_id}/set (batched practice) --------------------


def test_practice_set_returns_a_batch_grouped_under_one_set(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    inserted_sets = []
    generated = []
    counter = itertools.count(1)
    lock = threading.Lock()

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": inserted_sets.extend(rows)
        or [{"id": "set-1", **rows[0]}],
    )

    def fake_generate(**kwargs):
        # map_concurrent runs these on a thread pool, so the counter and the
        # capture list both need a lock to stay deterministic.
        with lock:
            generated.append(kwargs)
            n = next(counter)
        return {"id": f"item-{n}", "skillId": "skill-1", "bloomLevel": "apply",
                "prompt": "...", "choices": []}

    monkeypatch.setattr(practice.item_gen, "generate_question", fake_generate)

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set?size=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["courseId"] == "course-1"
    assert body["setId"] == "set-1"
    # map_concurrent preserves INPUT order of results, but these fake items
    # get their ids from a completion-order counter, so compare as a set.
    assert sorted(i["id"] for i in body["items"]) == ["item-1", "item-2", "item-3"]
    assert len(body["items"]) == 3
    # The set row is created before generation, sized to the request.
    assert inserted_sets == [{
        "institution_id": "institution-1", "course_id": "course-1",
        "skill_id": "skill-1", "kind": "practice", "size": 3,
    }]
    # Every generated item is grouped under the set at insert time.
    assert all(call["set_id"] == "set-1" for call in generated)
    assert all(call["kind"] == "practice" for call in generated)


def test_practice_set_defaults_to_five_items(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    generated = []
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "set-1", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {
            "id": f"item-{len(generated)}", "skillId": "skill-1",
            "bloomLevel": "apply", "prompt": "...", "choices": [],
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()["items"]) == 5


def test_practice_set_clamps_size_to_the_maximum(monkeypatch) -> None:
    """An oversized request must not fan out unbounded model calls — capped,
    not rejected, so a client asking for 50 still gets a usable set."""
    app.dependency_overrides[get_current_user] = authenticated_user
    generated = []
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "set-1", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {
            "id": f"item-{len(generated)}", "skillId": "skill-1",
            "bloomLevel": "apply", "prompt": "...", "choices": [],
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set?size=50")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(generated) == practice.MAX_SET_SIZE


def test_practice_set_rejects_a_non_positive_size(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set?size=0")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_practice_set_returns_empty_when_course_has_no_skills(monkeypatch) -> None:
    """Same guard as /next: no approved skill means nothing to generate
    against, so return an empty set and never create a set row."""
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.item_gen, "weakest_skill", lambda **kwargs: None)

    def fail_insert(*args, **kwargs):
        raise AssertionError("must not create a set row without a skill")

    monkeypatch.setattr(practice.db, "insert", fail_insert)

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "course-1", "setId": None, "items": []}


def test_practice_set_deletes_the_set_when_generation_fails(monkeypatch) -> None:
    """A failed batch must not leave a dangling set row behind — the grouping
    is removed, taking any partially-inserted items with it, and the error
    still surfaces as the same 502 the single-item path produces."""
    app.dependency_overrides[get_current_user] = authenticated_user
    deleted = []

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "set-1", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.db, "delete",
        lambda table, filters: deleted.append((table, filters)) or [],
    )

    def raise_invalid(**kwargs):
        raise ItemGenerationError("Kala could not create a valid question. Please try again.")

    monkeypatch.setattr(practice.item_gen, "generate_question", raise_invalid)

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert deleted == [("quiz_sets", {"id": "eq.set-1"})]


def test_practice_set_uses_an_explicit_skill_id_when_given(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.db, "select",
        lambda table, params: [{"id": "skill-7", "name": "Graphs", "bloom_level": "analyze"}],
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "set-1", **rows[0]}],
    )
    generated = []
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {
            "id": "item-1", "skillId": "skill-7", "bloomLevel": "analyze",
            "prompt": "...", "choices": [],
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set?skill_id=skill-7&size=1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert generated[0]["skill"]["id"] == "skill-7"


def test_practice_set_404s_an_unknown_skill_id(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set?skill_id=nope")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


# ---- POST /practice/{course_id}/set/from-items (study -> test bridge) ------


def test_set_from_items_groups_existing_items_without_generating(monkeypatch) -> None:
    """The bridge reuses studied items: it must NOT call generate_question,
    just wrap the existing rows in a quiz_sets grouping."""
    app.dependency_overrides[get_current_user] = authenticated_user
    inserted_sets = []
    updated = []
    generated = []

    monkeypatch.setattr(
        practice.db, "select",
        lambda table, params: [
            {"id": "item-1", "skill_id": "skill-1", "prompt": "Q1",
             "choices": [{"id": "a", "label": "A"}], "bloom_level": "apply"},
            {"id": "item-2", "skill_id": "skill-1", "prompt": "Q2",
             "choices": [{"id": "b", "label": "B"}], "bloom_level": "apply"},
        ],
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": inserted_sets.extend(rows)
        or [{"id": "set-1", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.db, "update",
        lambda table, filters, values: updated.append((filters, values)) or [],
    )
    # Any generation call is a bug for this endpoint.
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {"id": "nope"},
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/set/from-items",
                json={"item_ids": ["item-1", "item-2"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["setId"] == "set-1"
    assert [i["id"] for i in body["items"]] == ["item-1", "item-2"]
    assert inserted_sets == [{
        "institution_id": "institution-1", "course_id": "course-1",
        "skill_id": "skill-1", "kind": "practice", "size": 2,
    }]
    # Each studied item is re-pointed at the new set, and nothing was generated.
    assert updated == [
        ({"id": "eq.item-1"}, {"set_id": "set-1"}),
        ({"id": "eq.item-2"}, {"set_id": "set-1"}),
    ]
    assert generated == []


def test_set_from_items_404s_when_no_items_belong_here(monkeypatch) -> None:
    """Tenant safety: ids that aren't in this course/institution must not be
    grouped — the query returns nothing and the request 404s."""
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])

    def fail_insert(*args, **kwargs):
        raise AssertionError("must not create a set with no valid items")

    monkeypatch.setattr(practice.db, "insert", fail_insert)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/set/from-items",
                json={"item_ids": ["foreign-1"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_set_from_items_rejects_a_cross_skill_batch(monkeypatch) -> None:
    """A set is scoped to one skill (quiz_sets.skill_id is NOT NULL), so a
    mixed-skill bridge request is a 422, not a silently mislabeled set."""
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.db, "select",
        lambda table, params: [
            {"id": "item-1", "skill_id": "skill-1", "prompt": "Q1", "choices": [], "bloom_level": None},
            {"id": "item-2", "skill_id": "skill-2", "prompt": "Q2", "choices": [], "bloom_level": None},
        ],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/set/from-items",
                json={"item_ids": ["item-1", "item-2"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_set_from_items_422s_on_empty_ids(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    try:
        with TestClient(app) as client:
            response = client.post("/practice/course-1/set/from-items", json={"item_ids": []})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_list_sets_returns_saved_sets_newest_first(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    captured = {}

    def fake_select(table, params):
        if table == "quiz_set_attempts":
            # set-2 attempted once, correct; set-1 never attempted (absent).
            return [{"set_id": "set-2", "attempted_count": 3, "correct_count": 2,
                     "last_attempted_at": "2026-02-03T00:00:00Z"}]
        captured.update(params)
        return [
            {"id": "set-2", "skill_id": "skill-1", "kind": "practice", "size": 5,
             "created_at": "2026-02-02T00:00:00Z"},
            {"id": "set-1", "skill_id": "skill-1", "kind": "practice", "size": 3,
             "created_at": "2026-02-01T00:00:00Z"},
        ]

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/sets?skill_id=skill-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [s["setId"] for s in body["sets"]] == ["set-2", "set-1"]
    assert body["sets"][0]["size"] == 5
    # Attempt metadata is per-student and rides along on each set.
    assert body["sets"][0]["attemptedCount"] == 3
    assert body["sets"][0]["correctCount"] == 2
    assert body["sets"][0]["lastAttemptedAt"] == "2026-02-03T00:00:00Z"
    # Never attempted -> explicit nulls, not missing keys.
    assert body["sets"][1]["attemptedCount"] is None
    assert body["sets"][1]["correctCount"] is None
    assert captured["skill_id"] == "eq.skill-1"
    assert captured["order"] == "created_at.desc"


def test_get_set_returns_its_items_in_order(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "quiz_sets":
            return [{"id": "set-1", "skill_id": "skill-1", "kind": "practice",
                     "size": 2, "created_at": "2026-02-01T00:00:00Z"}]
        if table == "generated_items":
            return [
                {"id": "item-1", "skill_id": "skill-1", "prompt": "Q1",
                 "choices": [{"id": "a", "label": "A"}], "bloom_level": "apply"},
                {"id": "item-2", "skill_id": "skill-1", "prompt": "Q2",
                 "choices": [{"id": "b", "label": "B"}], "bloom_level": "apply"},
            ]
        return []

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/sets/set-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["setId"] == "set-1"
    assert [i["id"] for i in body["items"]] == ["item-1", "item-2"]
    # Never attempted in this fixture -> explicit nulls on the set metadata.
    assert body["attemptedCount"] is None
    assert body["correctCount"] is None
    assert body["lastAttemptedAt"] is None
    # The item payload must NEVER carry the answer key (graded test, not a
    # flashcard browse).
    for item in body["items"]:
        assert "correct_choice_id" not in item
        assert "explanation" not in item


def test_get_set_404s_for_another_course(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    # quiz_sets lookup filtered by course returns nothing -> 404, no items read.
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-2/sets/set-from-course-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


# ---- quiz_set_attempts bookkeeping ----------------------------------------


def test_submit_increments_set_attempts_when_item_belongs_to_a_set(monkeypatch) -> None:
    """A graded item grouped under a set must bump this student's attempt
    counters, while grading/evidence/tracer stay exactly as they were."""
    app.dependency_overrides[get_current_user] = authenticated_user
    upserted = []

    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1",
                          "correct": True, "explanation": "ok", "setId": "set-1"},
    )
    monkeypatch.setattr(practice.db, "insert_evidence", lambda rows: rows)
    monkeypatch.setattr(practice.tracer, "apply_evidence", lambda **kwargs: {"estimate": 0.5})
    # Existing row: 3 attempts / 1 correct before this answer.
    monkeypatch.setattr(
        practice.db, "select",
        lambda table, params: [{"attempted_count": 3, "correct_count": 1}],
    )
    monkeypatch.setattr(
        practice.db, "upsert",
        lambda table, rows, on_conflict: upserted.extend(rows) or rows,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/submit",
                json={"item_id": "item-1", "choice_id": "a", "latency_ms": 100},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert upserted[0]["attempted_count"] == 4
    assert upserted[0]["correct_count"] == 2
    assert upserted[0]["set_id"] == "set-1"
    assert "last_attempted_at" in upserted[0]


def test_submit_creates_a_fresh_attempt_row_when_none_exists(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    upserted = []
    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1",
                          "correct": False, "explanation": "no", "setId": "set-9"},
    )
    monkeypatch.setattr(practice.db, "insert_evidence", lambda rows: rows)
    monkeypatch.setattr(practice.tracer, "apply_evidence", lambda **kwargs: {"estimate": 0.2})
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])  # no row yet
    monkeypatch.setattr(
        practice.db, "upsert",
        lambda table, rows, on_conflict: upserted.extend(rows) or rows,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/submit",
                json={"item_id": "item-1", "choice_id": "b"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert upserted[0]["attempted_count"] == 1
    assert upserted[0]["correct_count"] == 0  # wrong answer still counts an attempt


def test_submit_of_an_ungrouped_item_touches_no_attempt_row(monkeypatch) -> None:
    """/next items have set_id null — submit must not create attempt rows for
    them (there is no set to attribute them to)."""
    app.dependency_overrides[get_current_user] = authenticated_user
    touched = []
    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1",
                          "correct": True, "explanation": "ok", "setId": None},
    )
    monkeypatch.setattr(practice.db, "insert_evidence", lambda rows: rows)
    monkeypatch.setattr(practice.tracer, "apply_evidence", lambda **kwargs: {"estimate": 0.5})
    monkeypatch.setattr(
        practice.db, "upsert",
        lambda *a, **k: touched.append(a) or [],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/course-1/submit",
                json={"item_id": "item-1", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert touched == []


def test_get_set_includes_this_students_attempt_row(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "quiz_sets":
            return [{"id": "set-1", "skill_id": "skill-1", "kind": "practice",
                     "size": 2, "created_at": "2026-02-01T00:00:00Z"}]
        if table == "generated_items":
            return [{"id": "item-1", "skill_id": "skill-1", "prompt": "Q1",
                     "choices": [], "bloom_level": "apply"}]
        if table == "quiz_set_attempts":
            return [{"set_id": "set-1", "attempted_count": 5, "correct_count": 4,
                     "last_attempted_at": "2026-02-03T09:00:00Z"}]
        return []

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/course-1/sets/set-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["attemptedCount"] == 5
    assert body["correctCount"] == 4
    assert body["lastAttemptedAt"] == "2026-02-03T09:00:00Z"
