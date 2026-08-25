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


def test_flashcards_deck_generates_a_card_per_skill(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        flashcards.db, "select",
        lambda table, params: [{"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}],
    )
    monkeypatch.setattr(
        flashcards.item_gen, "generate_flashcard",
        lambda **kwargs: {"id": "card-1", "skillId": "skill-1", "front": "Q", "back": "A"},
    )

    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/course-1/deck")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "course-1", "cards": [{"id": "card-1", "skillId": "skill-1", "front": "Q", "back": "A"}]}


def test_flashcards_review_records_self_reported_recall(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_rows = []
    monkeypatch.setattr(
        flashcards.db, "select",
        lambda table, params: [{"id": "card-1", "skill_id": "skill-1"}],
    )
    monkeypatch.setattr(flashcards.db, "insert_evidence", lambda rows: evidence_rows.extend(rows) or rows)
    tracer_calls = []
    monkeypatch.setattr(flashcards.tracer, "apply_evidence", lambda **kwargs: tracer_calls.append(kwargs))

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/review",
                json={"item_id": "card-1", "knew_it": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert evidence_rows[0]["type"] == "flashcard"
    assert evidence_rows[0]["correct"] is False
    assert tracer_calls[0]["correct"] is False
