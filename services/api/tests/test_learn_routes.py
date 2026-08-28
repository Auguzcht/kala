from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
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
    """With no due cards yet, the deck tops up with a fresh MCQ card per
    untracked skill, marks it 'new', and returns the schedule stats. Answer
    keys never appear in the response."""
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "skills":
            return [{"id": "skill-1", "name": "Recursion", "bloom_level": "apply",
                     "module_ref": "Module 1"}]
        if table == "srs_state":  # nothing tracked yet
            return []
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
    assert card["choices"] and "correct_choice_id" not in card
    assert body["stats"]["due"] == 0


def test_flashcards_review_grades_server_side_and_advances_schedule(monkeypatch) -> None:
    """Review grades against the stored key (not a client 'knew it'), writes a
    flashcard evidence_event with hint usage, moves the tracer, and advances
    the spaced-repetition schedule."""
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_rows = []
    tracer_calls = []

    monkeypatch.setattr(
        flashcards.item_gen, "grade",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1",
                          "correct": False, "explanation": "not quite"},
    )
    monkeypatch.setattr(flashcards.db, "insert_evidence", lambda rows: evidence_rows.extend(rows) or rows)
    monkeypatch.setattr(flashcards.tracer, "apply_evidence",
                        lambda **kwargs: tracer_calls.append(kwargs) or {"estimate": 0.3})
    monkeypatch.setattr(
        flashcards.srs, "review",
        lambda **kwargs: SimpleNamespace(graduated=False, interval_hours=4.0, box=0),
    )
    monkeypatch.setattr(
        flashcards.xp, "summary",
        lambda **kwargs: {"xp": 12, "streakDays": 1, "badges": [], "attempts": 6, "correct": 3},
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/review",
                json={"item_id": "card-1", "choice_id": "b", "hints_used": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["graduated"] is False
    assert body["dueInHours"] == 4.0
    assert body["reward"]["xp"] == 12
    assert evidence_rows[0]["type"] == "flashcard"
    assert evidence_rows[0]["correct"] is False
    assert evidence_rows[0]["hints_used"] == 1
    assert tracer_calls[0]["correct"] is False
