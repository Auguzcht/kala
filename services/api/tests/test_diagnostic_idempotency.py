from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="user-1", institution_id="inst-1", app_role="student")


def test_diagnostic_reuses_existing_items_and_never_regenerates_them(monkeypatch) -> None:
    """The core fix: a second fetch must return the SAME questions, not a
    freshly generated set. generate_question must not be called at all when
    every skill already has a diagnostic item."""
    app.dependency_overrides[get_current_user] = authenticated_user
    generate_calls = []

    def fake_select(table, params):
        if table == "skills":
            return [
                {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
                {"id": "skill-2", "name": "Iteration", "bloom_level": "apply"},
            ]
        if table == "generated_items":
            return [
                {"id": "item-1", "skill_id": "skill-1", "bloom_level": "apply",
                 "prompt": "Q1?", "choices": [{"id": "a", "label": "x"}]},
                {"id": "item-2", "skill_id": "skill-2", "bloom_level": "apply",
                 "prompt": "Q2?", "choices": [{"id": "a", "label": "y"}]},
            ]
        return []

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.item_gen, "generate_question",
                        lambda **kw: generate_calls.append(kw) or {})

    try:
        with TestClient(app) as client:
            first = client.get("/courses/course-1/diagnostic").json()
            second = client.get("/courses/course-1/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert generate_calls == []  # never regenerated — both skills already had items
    assert first == second  # identical across fetches
    assert [q["id"] for q in first["questions"]] == ["item-1", "item-2"]
    assert first["questions"][0]["prompt"] == "Q1?"
    assert "correct_choice_id" not in first["questions"][0]  # answer key never leaks


def test_diagnostic_only_generates_for_skills_missing_an_item(monkeypatch) -> None:
    """Mixed case: skill-1 already has an item, skill-2 does not. Only
    skill-2 should trigger generation."""
    app.dependency_overrides[get_current_user] = authenticated_user
    generated_for = []

    def fake_select(table, params):
        if table == "skills":
            return [
                {"id": "skill-1", "name": "Recursion", "bloom_level": "apply"},
                {"id": "skill-2", "name": "Iteration", "bloom_level": "apply"},
            ]
        if table == "generated_items":
            return [
                {"id": "item-1", "skill_id": "skill-1", "bloom_level": "apply",
                 "prompt": "Existing Q?", "choices": [{"id": "a", "label": "x"}]},
            ]
        return []

    def fake_generate(*, institution_id, course_id, skill, kind):
        generated_for.append(skill["id"])
        return {"id": "new-item", "skillId": skill["id"], "bloomLevel": "apply",
                "prompt": "Freshly generated Q?", "choices": []}

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.item_gen, "generate_question", fake_generate)

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert generated_for == ["skill-2"]  # only the missing one
    prompts = [q["prompt"] for q in response["questions"]]
    assert prompts == ["Existing Q?", "Freshly generated Q?"]  # order matches skills order


def test_diagnostic_generates_for_all_skills_when_none_exist(monkeypatch) -> None:
    """First-ever fetch: no existing items, so every skill generates —
    unchanged behavior from before the fix for the true first-run case."""
    app.dependency_overrides[get_current_user] = authenticated_user
    generated_for = []

    def fake_select(table, params):
        if table == "skills":
            return [{"id": "skill-1", "name": "Recursion", "bloom_level": "apply"}]
        if table == "generated_items":
            return []
        return []

    def fake_generate(*, institution_id, course_id, skill, kind):
        generated_for.append(skill["id"])
        return {"id": "item-x", "skillId": skill["id"], "bloomLevel": "apply",
                "prompt": "Q?", "choices": []}

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.item_gen, "generate_question", fake_generate)

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert generated_for == ["skill-1"]
    assert len(response["questions"]) == 1


def test_diagnostic_returns_empty_list_when_course_has_no_approved_skills(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = authenticated_user
    monkeypatch.setattr(diagnostic.db, "select", lambda table, params: [])

    try:
        with TestClient(app) as client:
            response = client.get("/courses/course-1/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert response == {"courseId": "course-1", "questions": []}
