import itertools
import threading
from datetime import datetime, timedelta, timezone

import pytest
from app.deps import CurrentUser, get_current_user
from app.learn.items import ItemGenerationError
from app.main import app
from app.routers import flashcards, practice
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def legacy_route_fixtures(monkeypatch):
    """Keep pre-async route fixtures focused on the set API response."""
    def enqueue(*, institution_id, course_id, skill_id, set_id, size):
        return [{
            "id": f"job-{offset}", "institution_id": institution_id,
            "course_id": course_id, "skill_id": skill_id, "kind": "practice",
            "set_id": set_id, "context_offset": offset, "status": "pending",
        } for offset in range(size)]

    monkeypatch.setattr(practice, "enqueue_practice", enqueue)
    monkeypatch.setattr(practice, "practice_jobs", lambda **kwargs: [])


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="00000000-0000-4000-8000-000000000040", institution_id="institution-1", app_role="student")


def test_practice_next_returns_none_when_course_has_no_skills(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.item_gen, "weakest_skill", lambda **kwargs: None)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"courseId": "00000000-0000-4000-8000-000000000001", "item": None}


def test_practice_next_generates_an_item_for_the_weakest_skill(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: {"id": "item-1", "skillId": "00000000-0000-4000-8000-000000000010", "bloomLevel": "apply",
                          "prompt": "...", "choices": []},
    )

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"]["id"] == "item-1"


def test_practice_next_returns_safe_502_when_generation_is_invalid(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.item_gen,
        "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )

    def raise_invalid(**kwargs):
        raise ItemGenerationError("Kala could not create a valid question. Please try again.")

    monkeypatch.setattr(practice.item_gen, "generate_question", raise_invalid)
    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/next")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Kala could not create a valid question. Please try again.",
    }


def test_practice_submit_uses_transactional_quiz_review_with_legacy_body(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    rpc_calls = []
    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "00000000-0000-4000-8000-000000000010", "courseId": "00000000-0000-4000-8000-000000000001", "correct": True, "explanation": "why"},
    )
    monkeypatch.setattr(practice.db, "rpc", lambda fn, args: rpc_calls.append((fn, args)) or [{
        "mastery_estimate": 0.65, "replayed": False,
    }])
    monkeypatch.setattr(practice, "record_exposure", lambda **kwargs: None)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/00000000-0000-4000-8000-000000000001/submit",
                json={"item_id": "item-1", "choice_id": "a", "latency_ms": 1200},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"correct": True, "explanation": "why", "mastery": 0.65}
    assert rpc_calls[0][0] == "review_flashcard"
    assert rpc_calls[0][1]["p_mode"] == "quiz"
    assert rpc_calls[0][1]["p_outcome"] == "good"
    assert rpc_calls[0][1]["p_latency_ms"] == 1200
    assert rpc_calls[0][1]["p_session_id"] is None
    assert rpc_calls[0][1]["p_idempotency_key"]


def test_practice_submit_404s_on_unknown_item(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user

    def raise_missing(**kwargs):
        raise ValueError("item not found")

    monkeypatch.setattr(practice.item_gen, "grade", raise_missing)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/00000000-0000-4000-8000-000000000001/submit",
                json={"item_id": "missing", "choice_id": "a"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_flashcards_deck_without_bank_returns_no_material_without_model_call(monkeypatch) -> None:
    """The legacy GET contract remains valid, but an unserved course does not
    make a synchronous generation call to fill the deck."""
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "skills":
            return [{"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply",
                     "module_ref": "Module 1"}]
        if table == "courses":
            return [{"id": "00000000-0000-4000-8000-000000000001", "bank_serving": False}]
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
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("study path called a model")),
    )

    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/00000000-0000-4000-8000-000000000001/deck")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["courseId"] == "00000000-0000-4000-8000-000000000001"
    assert body["cards"] == []
    assert body["bankStatus"] == {"status": "no_material", "mcqReady": 0}
    assert body["stats"]["due"] == 0


def test_flashcard_membership_is_read_only_and_includes_eligible_live_cards(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    skill_id = "00000000-0000-4000-8000-000000000010"
    bank_item = "00000000-0000-4000-8000-000000000021"
    legacy_item = "00000000-0000-4000-8000-000000000022"
    new_item = "00000000-0000-4000-8000-000000000023"
    selected = []
    items = [
        {"id": bank_item, "kind": "practice", "prompt": "Bank prompt", "choices": [{"id": "a", "label": "Answer"}],
         "correct_choice_id": "a", "explanation": "Because", "created_at": "2026-01-01T00:00:00Z"},
        {"id": legacy_item, "kind": "flashcard", "prompt": "Legacy prompt", "front": "Legacy front", "back": "Legacy back",
         "created_at": "2026-01-02T00:00:00Z"},
        {"id": new_item, "kind": "practice", "prompt": "New prompt", "choices": [{"id": "a", "label": "Answer"}],
         "correct_choice_id": "a", "created_at": "2026-01-03T00:00:00Z"},
    ]
    schedules = [
        {"item_id": bank_item, "box": 0, "ease_milli": 2500, "streak": 0, "reps": 1,
         "lapses": 1, "due_at": "2020-01-01T00:00:00Z", "last_outcome": "again"},
        {"item_id": legacy_item, "box": 4, "ease_milli": 2500, "streak": 4, "reps": 5,
         "lapses": 1, "due_at": "2099-01-01T00:00:00Z", "last_outcome": "good"},
    ]

    def fake_select(table, params):
        selected.append((table, params))
        if table == "skills": return [{"id": skill_id}]
        if table == "generated_items": return items
        if table == "srs_state": return schedules
        if table == "institutions": return [{"timezone": "Asia/Manila"}]
        return []

    monkeypatch.setattr(flashcards.db, "select", fake_select)
    def unexpected_write(*args, **kwargs):
        raise AssertionError("membership must be read-only")
    monkeypatch.setattr(flashcards.db, "insert", unexpected_write)
    monkeypatch.setattr(flashcards.db, "insert_evidence", unexpected_write)
    monkeypatch.setattr(flashcards.db, "rpc", unexpected_write)
    try:
        with TestClient(app) as client:
            response = client.get(f"/flashcards/00000000-0000-4000-8000-000000000001/skills/{skill_id}/cards")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["new"] == 1
    assert body["counts"]["learning"] == 1
    assert body["counts"]["known"] == 1
    assert body["counts"]["slipping"] == 0
    assert len(body["cards"]) == 3
    assert body["cards"][0]["back"] == {"label": "Answer", "explanation": "Because"}
    assert body["cards"][1]["back"]["label"] == "Legacy back"
    assert selected[1][1]["or"] == "(and(kind.eq.practice,origin.eq.bank),kind.eq.flashcard)"
    assert all(table not in ("evidence_events", "item_exposures") for table, _ in selected)


def test_flashcards_deck_bank_status_omits_usable(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    def fake_select(table, params):
        if table == "skills":
            return [{"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion",
                     "bloom_level": "apply", "module_ref": "Module 1"}]
        if table == "courses": return [{"id": "c", "bank_serving": True}]
        if table == "srs_state": return []
        if table == "skill_bank_state": return [{"status": "ready", "mcq_ready": 8, "mcq_target": 10}]
        return []
    monkeypatch.setattr(flashcards.db, "select", fake_select)
    monkeypatch.setattr(flashcards.srs, "due_cards", lambda **kwargs: [])
    monkeypatch.setattr(flashcards.srs, "stats", lambda **kwargs: {})
    monkeypatch.setattr(flashcards, "pick_bank_items", lambda *args, **kwargs: [])
    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/00000000-0000-4000-8000-000000000001/deck?skill_id=00000000-0000-4000-8000-000000000010")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["bankStatus"] == {"status": "ready", "mcqReady": 8}


def test_flashcards_study_all_is_capped_to_twenty_and_uses_atomic_daily_claim(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    skill_id = "00000000-0000-4000-8000-000000000010"
    items = [{"id": f"item-{n}", "skill_id": skill_id, "kind": "practice", "prompt": f"P{n}",
              "choices": [], "origin": "bank"} for n in range(25)]
    rpc_calls = []
    monkeypatch.setattr(flashcards, "_skill_map", lambda **kwargs: {skill_id: {"name": "Recursion"}})
    monkeypatch.setattr(flashcards, "_study_pool", lambda **kwargs: items)
    monkeypatch.setattr(flashcards.db, "select", lambda table, params: (
        [{"id": "course", "bank_serving": True}] if table == "courses" else
        [{"item_id": item_id, "box": 0, "ease_milli": 2500, "streak": 0, "reps": 0,
          "lapses": 0, "last_outcome": None, "due_at": datetime.now(timezone.utc).isoformat()}
         for item_id in params.get("item_id", "").removeprefix("in.(").removesuffix(")").split(",") if item_id]
        if table == "srs_state" and params.get("item_id", "").startswith("in.") else
        [{"id": item["id"], "kind": "practice", "correct_choice_id": None,
          "choices": [], "explanation": ""} for item in items]
        if table == "generated_items" else []
    ))
    monkeypatch.setattr(flashcards.db, "rpc", lambda name, args: rpc_calls.append((name, args)) or
                        [{"item_id": item["id"], "is_new": True} for item in items[:20]])
    monkeypatch.setattr(flashcards.srs, "stats", lambda **kwargs: {"due": 0})
    monkeypatch.setattr(flashcards, "record_exposure", lambda **kwargs: None)
    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/00000000-0000-4000-8000-000000000001/deck?mode=all&limit=40")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body["cards"]) == 20
    assert body["mode"] == "all"
    assert body["limit"] == 20
    assert body["hasMore"] is True
    assert body["sessionId"]
    assert rpc_calls[0][0] == "claim_study_cards"
    assert len(rpc_calls[0][1]["p_item_ids"]) == 20
    assert rpc_calls[0][1]["p_daily_new_cap"] == 20


def test_flashcards_review_mode_puts_slipping_before_most_overdue(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    skill_id = "00000000-0000-4000-8000-000000000010"
    due = [
        {"item_id": "older-learning", "skill_id": skill_id, "box": 1, "ease_milli": 2500,
         "streak": 1, "reps": 2, "lapses": 0, "last_outcome": "good", "due_at": "2020-01-01T00:00:00Z"},
        {"item_id": "slipping", "skill_id": skill_id, "box": 0, "ease_milli": 2500,
         "streak": 0, "reps": 3, "lapses": 1, "last_outcome": "again", "due_at": "2026-01-01T00:00:00Z"},
        {"item_id": "recent-learning", "skill_id": skill_id, "box": 1, "ease_milli": 2500,
         "streak": 1, "reps": 1, "lapses": 0, "last_outcome": "good", "due_at": "2025-01-01T00:00:00Z"},
    ]
    items = [{"id": row["item_id"], "skill_id": skill_id, "prompt": row["item_id"],
              "choices": [{"id": "a", "label": "Answer"}]} for row in due]
    monkeypatch.setattr(flashcards, "_skill_map", lambda **kwargs: {skill_id: {"name": "Recursion"}})
    monkeypatch.setattr(flashcards.srs, "due_cards", lambda **kwargs: due)
    monkeypatch.setattr(flashcards.srs, "stats", lambda **kwargs: {"due": 3})
    monkeypatch.setattr(flashcards, "pick_bank_items", lambda *args, **kwargs: [])
    monkeypatch.setattr(flashcards, "record_exposure", lambda **kwargs: None)
    monkeypatch.setattr(flashcards.db, "select", lambda table, params: (
        [{"id": "course", "bank_serving": True}] if table == "courses" else
        items if table == "generated_items" else
        [{"timezone": "Asia/Manila"}] if table == "institutions" else []
    ))
    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/00000000-0000-4000-8000-000000000001/deck?mode=review&limit=3")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert [card["itemId"] for card in response.json()["cards"]] == [
        "slipping", "older-learning", "recent-learning",
    ]


def test_course_memory_summary_counts_membership_without_writing(monkeypatch) -> None:
    from app.routers import courses

    app.dependency_overrides[get_current_user] = authenticated_user
    skill = "00000000-0000-4000-8000-000000000010"
    items = [
        {"id": "new", "skill_id": skill},
        {"id": "slipping", "skill_id": skill},
        {"id": "learning", "skill_id": skill},
        {"id": "known", "skill_id": skill},
    ]
    schedules = [
        {"item_id": "slipping", "box": 0, "ease_milli": 2500, "streak": 0, "reps": 2,
         "lapses": 1, "last_outcome": "again", "due_at": "2020-01-01T00:00:00Z"},
        {"item_id": "learning", "box": 0, "ease_milli": 2500, "streak": 0, "reps": 1,
         "lapses": 1, "last_outcome": "again", "due_at": "2020-01-01T00:00:00Z"},
        {"item_id": "known", "box": 5, "ease_milli": 2500, "streak": 3, "reps": 3,
         "lapses": 0, "last_outcome": "good", "due_at": "2099-01-01T00:00:00Z"},
    ]
    monkeypatch.setattr(courses.db, "select", lambda table, params: (
        [{"id": skill, "name": "Recursion"}] if table == "skills" else
        items if table == "generated_items" else
        schedules if table == "srs_state" else
        [{"timezone": "Asia/Manila"}] if table == "institutions" else []
    ))
    def no_writes(*args, **kwargs):
        raise AssertionError("memory summary must be read-only")
    monkeypatch.setattr(courses.db, "rpc", no_writes)
    monkeypatch.setattr(courses.db, "insert", no_writes)
    try:
        with TestClient(app) as client:
            response = client.get("/courses/00000000-0000-4000-8000-000000000001/memory/summary")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["totals"] == {
        "new": 1, "learning": 1, "slipping": 1, "known": 1, "dueToday": 2,
    }


def test_flashcards_review_is_a_self_mark_that_never_moves_the_twin(monkeypatch) -> None:
    """Study mode is not assessment. Review writes a flashcard evidence_event
    (correct=remembered, so the research export still sees study behavior) and
    advances the spaced-repetition schedule, but NEVER calls the tracer —
    mastery must not move on a self-report."""
    app.dependency_overrides[get_current_user] = authenticated_user
    rpc_calls = []

    monkeypatch.setattr(
        flashcards.db, "select",
        lambda table, params: [{"id": "card-1", "skill_id": "00000000-0000-4000-8000-000000000010"}],
    )
    # The module must not even import the tracer any more — that is the
    # strongest form of "study never moves mastery": there is no code path
    # that could call it, not merely a path that happens not to.
    assert not hasattr(flashcards, "tracer")
    due_at = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    monkeypatch.setattr(
        flashcards.db, "rpc",
        lambda fn, args: rpc_calls.append((fn, args)) or [{
            "counted": True, "was_due": True, "box": 0, "ease_milli": 2300,
            "streak": 0, "reps": 1, "lapses": 1, "last_outcome": "again",
            "due_at": due_at, "graduated": False, "replayed": False,
        }],
    )
    monkeypatch.setattr(flashcards, "record_exposure", lambda **kwargs: None)
    monkeypatch.setattr(
        flashcards.xp, "summary",
        lambda **kwargs: {"xp": 12, "streakDays": 1, "badges": [], "attempts": 6, "correct": 3},
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/00000000-0000-4000-8000-000000000001/review",
                json={"item_id": "card-1", "remembered": False, "latency_ms": 900},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["remembered"] is False
    assert body["graduated"] is False
    assert body["dueInHours"] == 9.2
    assert body["reward"]["xp"] == 12
    # No `correct`/`mastery` in the response — study does not grade.
    assert "correct" not in body
    assert "mastery" not in body
    # The legacy request still maps its rating into the atomic service RPC.
    assert rpc_calls[0][0] == "review_flashcard"
    assert rpc_calls[0][1]["p_outcome"] == "again"
    assert rpc_calls[0][1]["p_latency_ms"] == 900
    assert rpc_calls[0][1]["p_mode"] == "flashcard"
    assert rpc_calls[0][1]["p_session_id"] is None
    assert rpc_calls[0][1]["p_idempotency_key"]
    # ...and the twin is never touched (no tracer import exists to call).


def test_flashcard_review_accepts_additive_memory_fields(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    rpc_calls = []
    due_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    monkeypatch.setattr(flashcards.db, "select", lambda table, params: [{
        "id": "card-1", "skill_id": "00000000-0000-4000-8000-000000000010",
    }])
    monkeypatch.setattr(flashcards.db, "rpc", lambda fn, args: rpc_calls.append(args) or [{
        "counted": True, "was_due": True, "box": 1, "ease_milli": 2560,
        "streak": 1, "reps": 1, "lapses": 0, "last_outcome": "good",
        "due_at": due_at, "graduated": False, "replayed": False,
    }])
    monkeypatch.setattr(flashcards, "record_exposure", lambda **kwargs: None)
    monkeypatch.setattr(flashcards.xp, "summary", lambda **kwargs: {"xp": 12})
    try:
        with TestClient(app) as client:
            response = client.post(
                "/flashcards/00000000-0000-4000-8000-000000000001/review",
                json={"item_id": "card-1", "outcome": "good", "session_id": "00000000-0000-4000-8000-000000000099",
                      "idempotency_key": "attempt-1", "mode": "flashcard"},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["remembered"] is True
    assert response.json()["counted"] is True
    assert response.json()["state"] == "learning"
    assert rpc_calls[0]["p_outcome"] == "good"
    assert rpc_calls[0]["p_session_id"] == "00000000-0000-4000-8000-000000000099"
    assert rpc_calls[0]["p_idempotency_key"] == "attempt-1"


# ---- POST /practice/{course_id}/set (batched practice) --------------------


def test_practice_set_returns_a_batch_grouped_under_one_set(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    inserted_sets = []
    generated = []
    counter = itertools.count(1)
    lock = threading.Lock()

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": inserted_sets.extend(rows)
        or [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )

    def fake_generate(**kwargs):
        # map_concurrent runs these on a thread pool, so the counter and the
        # capture list both need a lock to stay deterministic.
        with lock:
            generated.append(kwargs)
            n = next(counter)
        return {"id": f"item-{n}", "skillId": "00000000-0000-4000-8000-000000000010", "bloomLevel": "apply",
                "prompt": "...", "choices": []}

    monkeypatch.setattr(practice.item_gen, "generate_question", fake_generate)

    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?size=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["courseId"] == "00000000-0000-4000-8000-000000000001"
    assert body["setId"] == "00000000-0000-4000-8000-000000000020"
    assert body["status"] == "generating"
    assert body["requestedSize"] == 3
    assert body["readyCount"] == 0
    assert body["pendingCount"] == 3
    assert body["items"] == []
    # The set row is created before queue rows, sized to the request.
    assert inserted_sets == [{
        "institution_id": "institution-1", "course_id": "00000000-0000-4000-8000-000000000001",
        "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice", "size": 3,
    }]
    assert generated == []


def test_practice_set_defaults_to_five_items(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    generated = []
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {
            "id": f"item-{len(generated)}", "skillId": "00000000-0000-4000-8000-000000000010",
            "bloomLevel": "apply", "prompt": "...", "choices": [],
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["requestedSize"] == 5


def test_practice_set_clamps_size_to_the_maximum(monkeypatch) -> None:
    """An oversized request must not fan out unbounded model calls — capped,
    not rejected, so a client asking for 50 still gets a usable set."""
    app.dependency_overrides[get_current_user] = authenticated_user
    generated = []
    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )
    monkeypatch.setattr(
        practice.item_gen, "generate_question",
        lambda **kwargs: generated.append(kwargs) or {
            "id": f"item-{len(generated)}", "skillId": "00000000-0000-4000-8000-000000000010",
            "bloomLevel": "apply", "prompt": "...", "choices": [],
        },
    )

    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?size=50")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["requestedSize"] == practice.MAX_SET_SIZE


def test_practice_set_rejects_a_non_positive_size(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?size=0")
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
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["setId"] is None
    assert response.json()["status"] == "failed"


def test_practice_set_returns_before_generation_runs(monkeypatch) -> None:
    """The route persists the grouping and queue, then returns immediately."""
    app.dependency_overrides[get_current_user] = authenticated_user

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )
    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "generating"


def test_practice_set_uses_an_explicit_skill_id_when_given(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(
        practice.db, "select",
        lambda table, params: [{"id": "skill-7", "name": "Graphs", "bloom_level": "analyze"}],
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
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
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?skill_id=skill-7&size=1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["skillId"] == "skill-7"


def test_practice_set_404s_an_unknown_skill_id(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?skill_id=nope")
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
    selected_params = []

    def select_items(table, params):
        selected_params.append((table, params))
        return [
            {"id": "item-1", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q1",
             "choices": [{"id": "a", "label": "A"}], "bloom_level": "apply"},
            {"id": "item-2", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q2",
             "choices": [{"id": "b", "label": "B"}], "bloom_level": "apply"},
        ]

    monkeypatch.setattr(practice.db, "select", select_items)
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": inserted_sets.extend(rows)
        or [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
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
                "/practice/00000000-0000-4000-8000-000000000001/set/from-items",
                json={"item_ids": ["item-1", "item-2"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["setId"] == "00000000-0000-4000-8000-000000000020"
    assert [i["id"] for i in body["items"]] == ["item-1", "item-2"]
    assert inserted_sets == [{
        "institution_id": "institution-1", "course_id": "00000000-0000-4000-8000-000000000001",
        "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice", "size": 2,
    }, {"set_id": "00000000-0000-4000-8000-000000000020", "item_id": "item-1", "position": 0},
       {"set_id": "00000000-0000-4000-8000-000000000020", "item_id": "item-2", "position": 1}]
    assert updated == []
    assert generated == []
    _, filter_params = selected_params[0]
    assert filter_params["retired_at"] == "is.null"
    assert filter_params["skills.status"] == "eq.approved"


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
                "/practice/00000000-0000-4000-8000-000000000001/set/from-items",
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
            {"id": "item-1", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q1", "choices": [], "bloom_level": None},
            {"id": "item-2", "skill_id": "00000000-0000-4000-8000-000000000011", "prompt": "Q2", "choices": [], "bloom_level": None},
        ],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/00000000-0000-4000-8000-000000000001/set/from-items",
                json={"item_ids": ["item-1", "item-2"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_set_from_items_422s_on_empty_ids(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set/from-items", json={"item_ids": []})
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
        if table == "generated_items":
            # The count is now DERIVED from the items, not read off the
            # quiz_sets.size column (which can go stale when a partial batch's
            # correction is missed). set-2 really holds 5, set-1 holds 3.
            return ({"set_id": s} for s in
                    ["set-2"] * 5 + ["00000000-0000-4000-8000-000000000020"] * 3)
        captured.update(params)
        return [
            {"id": "set-2", "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice", "size": 5,
             "created_at": "2026-02-02T00:00:00Z"},
            {"id": "00000000-0000-4000-8000-000000000020", "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice", "size": 3,
             "created_at": "2026-02-01T00:00:00Z"},
        ]

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/sets?skill_id=skill-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [s["setId"] for s in body["sets"]] == ["set-2", "00000000-0000-4000-8000-000000000020"]
    assert body["sets"][0]["size"] == 5
    assert body["sets"][1]["size"] == 3
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
            return [{"id": "00000000-0000-4000-8000-000000000020", "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice",
                     "size": 2, "created_at": "2026-02-01T00:00:00Z"}]
        if table == "generated_items":
            return [
                {"id": "item-1", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q1",
                 "choices": [{"id": "a", "label": "A"}], "bloom_level": "apply"},
                {"id": "item-2", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q2",
                 "choices": [{"id": "b", "label": "B"}], "bloom_level": "apply"},
            ]
        return []

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/sets/00000000-0000-4000-8000-000000000020")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["setId"] == "00000000-0000-4000-8000-000000000020"
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


def test_saved_set_with_only_retired_items_is_unavailable(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    generated_filters = []
    def fake_select(table, params):
        if table == "quiz_sets":
            return [{"id": "00000000-0000-4000-8000-000000000020", "skill_id": "skill-1",
                     "kind": "practice", "size": 1, "created_at": "2026-02-01T00:00:00Z"}]
        if table == "quiz_set_items":
            return [{"item_id": "retired-1", "position": 0}]
        if table == "generated_items":
            generated_filters.append(params)
            return []
        return []
    monkeypatch.setattr(practice.db, "select", fake_select)
    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/sets/00000000-0000-4000-8000-000000000020")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["available"] is False
    assert response.json()["items"] == []
    assert generated_filters[0]["retired_at"] == "is.null"
    assert generated_filters[0]["skills.status"] == "eq.approved"


def test_saved_set_counts_only_live_approved_items(monkeypatch) -> None:
    calls = []
    def select(table, params):
        calls.append((table, params))
        if table == "quiz_set_items":
            return [{"set_id": "set-1", "item_id": "live"},
                    {"set_id": "set-1", "item_id": "retired"}]
        if table == "generated_items":
            return [{"id": "live"}]
        return []
    monkeypatch.setattr(practice.db, "select", select)
    assert practice._item_counts_by_set(institution_id="inst", set_ids=["set-1"]) == {"set-1": 1}
    item_params = calls[-1][1]
    assert item_params["retired_at"] == "is.null"
    assert item_params["skills.status"] == "eq.approved"


def test_flashcard_due_rows_cannot_reintroduce_retired_items(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    item_queries = []
    def select(table, params):
        if table == "skills":
            return [{"id": "skill-1", "name": "Skill", "bloom_level": "apply"}]
        if table == "courses":
            return [{"id": "course", "bank_serving": False}]
        if table == "srs_state":
            return [{"item_id": "tracked", "skill_id": "skill-1"}]
        if table == "generated_items":
            item_queries.append(params)
            return []
        return []
    monkeypatch.setattr(flashcards.db, "select", select)
    monkeypatch.setattr(flashcards.srs, "due_cards", lambda **kwargs: [
        {"item_id": "retired-1", "skill_id": "skill-1", "box": 2}
    ])
    monkeypatch.setattr(flashcards.srs, "stats", lambda **kwargs: {})
    monkeypatch.setattr(flashcards.srs, "_active_item_ids", lambda **kwargs: {"tracked"})
    try:
        with TestClient(app) as client:
            response = client.get("/flashcards/00000000-0000-4000-8000-000000000001/deck?skill_id=skill-1")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["cards"] == []
    assert item_queries[0]["retired_at"] == "is.null"
    assert item_queries[0]["skills.status"] == "eq.approved"


def test_get_set_404s_for_another_course(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    # quiz_sets lookup filtered by course returns nothing -> 404, no items read.
    monkeypatch.setattr(practice.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000002/sets/set-from-course-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


# ---- quiz_set_attempts bookkeeping ----------------------------------------


def test_submit_increments_set_attempts_when_item_belongs_to_a_set(monkeypatch) -> None:
    """A graded item grouped under a set must bump this student's attempt
    counters, while the atomic grading/evidence/mastery RPC remains separate."""
    app.dependency_overrides[get_current_user] = authenticated_user
    upserted = []
    rpc_calls = []

    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "00000000-0000-4000-8000-000000000010", "courseId": "00000000-0000-4000-8000-000000000001",
                          "correct": True, "explanation": "ok"},
    )
    monkeypatch.setattr(practice.db, "rpc", lambda fn, args: rpc_calls.append(args) or [{
        "mastery_estimate": 0.5, "replayed": False,
    }])
    monkeypatch.setattr(practice, "record_exposure", lambda **kwargs: None)
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
                "/practice/00000000-0000-4000-8000-000000000001/submit",
                json={"item_id": "item-1", "choice_id": "a", "latency_ms": 100,
                      "set_id": "00000000-0000-4000-8000-000000000020",
                      "idempotency_key": "attempt-set-1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert upserted[0]["attempted_count"] == 4
    assert upserted[0]["correct_count"] == 2
    assert upserted[0]["set_id"] == "00000000-0000-4000-8000-000000000020"
    assert "last_attempted_at" in upserted[0]
    assert rpc_calls[0]["p_session_id"] == "00000000-0000-4000-8000-000000000020"
    assert rpc_calls[0]["p_idempotency_key"] == "attempt-set-1"
    assert rpc_calls[0]["p_mode"] == "quiz"


def test_submit_creates_a_fresh_attempt_row_when_none_exists(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    upserted = []
    monkeypatch.setattr(
        practice.item_gen, "grade",
        lambda **kwargs: {"skillId": "00000000-0000-4000-8000-000000000010", "courseId": "00000000-0000-4000-8000-000000000001",
                          "correct": False, "explanation": "no", "setId": "set-9"},
    )
    monkeypatch.setattr(practice.db, "rpc", lambda fn, args: [{"mastery_estimate": 0.2, "replayed": False}])
    monkeypatch.setattr(practice, "record_exposure", lambda **kwargs: None)
    def no_attempt_but_valid_set(table, params):
        if table == "quiz_set_items":
            return [{"set_id": "00000000-0000-4000-8000-000000000020"}]
        return []
    monkeypatch.setattr(practice.db, "select", no_attempt_but_valid_set)
    monkeypatch.setattr(
        practice.db, "upsert",
        lambda table, rows, on_conflict: upserted.extend(rows) or rows,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/00000000-0000-4000-8000-000000000001/submit",
                json={"item_id": "item-1", "choice_id": "b", "set_id": "00000000-0000-4000-8000-000000000020"},
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
        lambda **kwargs: {"skillId": "00000000-0000-4000-8000-000000000010", "courseId": "00000000-0000-4000-8000-000000000001",
                          "correct": True, "explanation": "ok", "setId": None},
    )
    monkeypatch.setattr(practice.db, "rpc", lambda fn, args: [{"mastery_estimate": 0.5, "replayed": False}])
    monkeypatch.setattr(practice, "record_exposure", lambda **kwargs: None)
    monkeypatch.setattr(
        practice.db, "upsert",
        lambda *a, **k: touched.append(a) or [],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/practice/00000000-0000-4000-8000-000000000001/submit",
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
            return [{"id": "00000000-0000-4000-8000-000000000020", "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice",
                     "size": 2, "created_at": "2026-02-01T00:00:00Z"}]
        if table == "generated_items":
            return [{"id": "item-1", "skill_id": "00000000-0000-4000-8000-000000000010", "prompt": "Q1",
                     "choices": [], "bloom_level": "apply"}]
        if table == "quiz_set_attempts":
            return [{"set_id": "00000000-0000-4000-8000-000000000020", "attempted_count": 5, "correct_count": 4,
                     "last_attempted_at": "2026-02-03T09:00:00Z"}]
        return []

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/sets/00000000-0000-4000-8000-000000000020")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["attemptedCount"] == 5
    assert body["correctCount"] == 4
    assert body["lastAttemptedAt"] == "2026-02-03T09:00:00Z"


def test_practice_set_is_not_resolved_by_the_create_request(monkeypatch) -> None:
    """Partial completion is reported by the existing set-detail poll target."""
    app.dependency_overrides[get_current_user] = authenticated_user

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )
    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?size=5")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["setId"] == "00000000-0000-4000-8000-000000000020"
    assert body["status"] == "generating"
    assert body["readyCount"] == 0
    assert body["pendingCount"] == 5


def test_practice_set_does_not_surface_worker_failure_at_enqueue_time(monkeypatch) -> None:
    """Worker failures are read later through GET /sets/{set_id}."""
    app.dependency_overrides[get_current_user] = authenticated_user

    monkeypatch.setattr(
        practice.item_gen, "weakest_skill",
        lambda **kwargs: {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion", "bloom_level": "apply"},
    )
    monkeypatch.setattr(
        practice.db, "insert",
        lambda table, rows, prefer="return=representation": [{"id": "00000000-0000-4000-8000-000000000020", **rows[0]}],
    )
    try:
        with TestClient(app) as client:
            response = client.post("/practice/00000000-0000-4000-8000-000000000001/set?size=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "generating"


def test_list_sets_reports_actual_item_count_not_the_stale_size_column(monkeypatch) -> None:
    """The bug this fixes: quiz_sets.size is written at creation and corrected
    after a partial batch, but a correction can be missed (a Lambda timing out
    mid-request), so a set could claim 5 questions while holding 3. The list
    must report what is actually there."""
    app.dependency_overrides[get_current_user] = authenticated_user

    def fake_select(table, params):
        if table == "quiz_set_attempts":
            return []
        if table == "generated_items":
            return [{"set_id": "set-stale"}] * 3  # only 3 items really exist
        return [{"id": "set-stale", "skill_id": "00000000-0000-4000-8000-000000000010", "kind": "practice",
                 "size": 5, "created_at": "2026-02-02T00:00:00Z",  # column lies
                 }]

    monkeypatch.setattr(practice.db, "select", fake_select)

    try:
        with TestClient(app) as client:
            response = client.get("/practice/00000000-0000-4000-8000-000000000001/sets")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["sets"][0]["size"] == 3  # derived, not the column's 5
