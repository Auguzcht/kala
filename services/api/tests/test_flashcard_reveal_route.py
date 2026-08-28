from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import flashcards


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="user-1", institution_id="institution-1", app_role="student")


def test_reveal_writes_a_lapse_before_returning_the_answer(monkeypatch) -> None:
    """The whole point of this endpoint: evidence + schedule must reflect a
    miss no matter what the answer turns out to be — there is no free peek."""
    app.dependency_overrides[get_current_user] = authenticated_user
    evidence_rows = []
    tracer_calls = []
    srs_calls = []

    monkeypatch.setattr(
        flashcards.item_gen, "reveal",
        lambda **kwargs: {"skillId": "skill-1", "courseId": "course-1",
                          "correctChoiceId": "b", "correctLabel": "Photosynthesis",
                          "explanation": "because b"},
    )
    monkeypatch.setattr(flashcards.db, "insert_evidence",
                        lambda rows: evidence_rows.extend(rows) or rows)
    monkeypatch.setattr(
        flashcards.tracer, "apply_evidence",
        lambda **kwargs: tracer_calls.append(kwargs) or {"estimate": 0.2},
    )
    monkeypatch.setattr(
        flashcards.srs, "review",
        lambda **kwargs: srs_calls.append(kwargs) or SimpleNamespace(
            graduated=False, interval_hours=4.0, box=0,
        ),
    )
    monkeypatch.setattr(
        flashcards.xp, "summary",
        lambda **kwargs: {"xp": 4, "streakDays": 1, "badges": [], "attempts": 1, "correct": 0},
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/reveal",
                json={"item_id": "card-1", "latency_ms": 500},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["revealed"] is True
    assert body["correctLabel"] == "Photosynthesis"
    assert body["box"] == 0
    assert body["reward"]["xp"] == 4

    # The lapse was committed as correct=False, unconditionally.
    assert evidence_rows[0]["type"] == "flashcard"
    assert evidence_rows[0]["correct"] is False
    assert tracer_calls[0]["correct"] is False
    assert srs_calls[0]["correct"] is False


def test_reveal_404s_on_unknown_item(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user

    def raise_missing(**kwargs):
        raise ValueError("item not found")

    monkeypatch.setattr(flashcards.item_gen, "reveal", raise_missing)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/reveal",
                json={"item_id": "missing"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_reveal_never_exposes_more_than_the_single_correct_label(monkeypatch) -> None:
    """Response shape check: no raw choices/prompt duplicated back, no other
    item internals — the client already has the card from GET /deck."""
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        flashcards.item_gen, "reveal",
        lambda **kwargs: {"skillId": "s-1", "courseId": "course-1",
                          "correctChoiceId": "a", "correctLabel": "X", "explanation": "y"},
    )
    monkeypatch.setattr(flashcards.db, "insert_evidence", lambda rows: rows)
    monkeypatch.setattr(flashcards.tracer, "apply_evidence", lambda **kw: {"estimate": 0.1})
    monkeypatch.setattr(flashcards.srs, "review",
                        lambda **kw: SimpleNamespace(graduated=False, interval_hours=4.0, box=0))
    monkeypatch.setattr(flashcards.xp, "summary", lambda **kw: {"xp": 0})

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/course-1/reveal", json={"item_id": "card-1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert set(response.json().keys()) == {
        "revealed", "correctChoiceId", "correctLabel", "explanation",
        "dueInHours", "box", "mastery", "reward",
    }
