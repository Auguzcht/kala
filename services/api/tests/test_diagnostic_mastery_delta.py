from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic


def authenticated_user() -> CurrentUser:
    return CurrentUser(user_id="00000000-0000-4000-8000-000000000040", institution_id="inst-1", app_role="student")


def test_submit_diagnostic_returns_mastery_delta_per_skill(monkeypatch) -> None:
    """submit_diagnostic must report the before/after band for every skill
    the submission touched: a skill with no prior mastery_state row reports
    priorBand 'no-evidence' (never a fabricated 0.0), and a skill with an
    existing estimate reports its real prior band."""
    app.dependency_overrides[get_current_user] = authenticated_user

    graded_by_item = {
        "item-1": {"skillId": "00000000-0000-4000-8000-000000000010", "courseId": "00000000-0000-4000-8000-000000000001", "correct": True, "explanation": "ok"},
        "item-2": {"skillId": "00000000-0000-4000-8000-000000000011", "courseId": "00000000-0000-4000-8000-000000000001", "correct": False, "explanation": "no"},
    }

    def fake_select(table, params):
        if table == "mastery_state":
            # Only skill-1 has prior evidence; skill-2 is brand new.
            return [{"skill_id": "00000000-0000-4000-8000-000000000010", "estimate": 0.5}]
        if table == "skills":
            return [
                {"id": "00000000-0000-4000-8000-000000000010", "name": "Recursion"},
                {"id": "00000000-0000-4000-8000-000000000011", "name": "Iteration"},
            ]
        return []

    def fake_apply_evidence(*, institution_id, user_id, course_id, skill_id, correct):
        # Deterministic posteriors: skill-1 moves proficient -> mastered,
        # skill-2 moves no-evidence -> developing.
        posterior = {"00000000-0000-4000-8000-000000000010": 0.75, "00000000-0000-4000-8000-000000000011": 0.15}
        return {"estimate": posterior[skill_id]}

    monkeypatch.setattr(diagnostic.db, "select", fake_select)
    monkeypatch.setattr(diagnostic.db, "insert_evidence", lambda rows: rows)
    monkeypatch.setattr(diagnostic.item_gen, "grade",
                        lambda **kw: graded_by_item[kw["item_id"]])
    monkeypatch.setattr(diagnostic.tracer, "apply_evidence", fake_apply_evidence)

    try:
        with TestClient(app) as client:
            response = client.post("/courses/00000000-0000-4000-8000-000000000001/diagnostic/submit", json={
                "answers": [
                    {"item_id": "item-1", "choice_id": "a", "latency_ms": 100},
                    {"item_id": "item-2", "choice_id": "b", "latency_ms": 200},
                ],
            }).json()
    finally:
        app.dependency_overrides.clear()

    delta_by_skill = {d["skillId"]: d for d in response["masteryDelta"]}

    assert delta_by_skill["00000000-0000-4000-8000-000000000010"]["priorEstimate"] == 0.5
    assert delta_by_skill["00000000-0000-4000-8000-000000000010"]["priorBand"] == "proficient"
    assert delta_by_skill["00000000-0000-4000-8000-000000000010"]["posteriorEstimate"] == 0.75
    assert delta_by_skill["00000000-0000-4000-8000-000000000010"]["posteriorBand"] == "mastered"

    assert delta_by_skill["00000000-0000-4000-8000-000000000011"]["priorEstimate"] is None
    assert delta_by_skill["00000000-0000-4000-8000-000000000011"]["priorBand"] == "no-evidence"
    assert delta_by_skill["00000000-0000-4000-8000-000000000011"]["posteriorEstimate"] == 0.15
    assert delta_by_skill["00000000-0000-4000-8000-000000000011"]["posteriorBand"] == "developing"
