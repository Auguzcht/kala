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
