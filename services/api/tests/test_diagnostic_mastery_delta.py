from fastapi.testclient import TestClient

from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic

# Course used by the partial-tolerance tests below.
_COURSE = "00000000-0000-4000-8000-000000000001"


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


# ---------------------------------------------------------------------------
# Partial tolerance: one bad skill must shorten the sitting, never 503 it.
#
# This is the bug the bank reset exposed. get_diagnostic used map_concurrent
# (all-or-nothing), so a single skill with no retrievable content raised
# NoCourseContentError and took down the whole 10-question baseline. While
# generated_items held spare diagnostic rows the GET read them cheaply and
# never reached generation, so the fault was invisible; clearing the bank
# removed that buffer.
# ---------------------------------------------------------------------------


def _diag_harness(monkeypatch, *, n_skills: int, failing: set[int]):
    """Wire get_diagnostic to n synthetic skills with durable queue rows."""
    from app.routers import diagnostic as diag

    skills = [
        {
            "id": f"00000000-0000-4000-8000-0000000003{i:02d}",
            "name": f"Skill{i}", "bloom_level": "apply",
        }
        for i in range(n_skills)
    ]
    bad_ids = {skills[i]["id"] for i in failing}

    monkeypatch.setattr(
        diag.db, "select",
        lambda table, params: skills if table == "skills" else [],
    )

    def fake_enqueue(*, skill_id, **kw):
        return ({
            "id": f"job-{skill_id}",
            "status": "failed" if skill_id in bad_ids else "pending",
        }, True)

    monkeypatch.setattr(diag, "enqueue_diagnostic", fake_enqueue)
    return skills


def test_one_contentless_skill_shortens_the_sitting_instead_of_503ing(
    monkeypatch,
) -> None:
    """The exact regression. Before: a 503 for the whole baseline because one
    skill had no material. After: the other questions still serve."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.deps import get_current_user, CurrentUser

    _diag_harness(monkeypatch, n_skills=5, failing={2})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id="64a59889-ba9c-44ae-87c8-765f86c92c78", app_role="student",
    )
    try:
        with TestClient(app) as client:
            resp = client.get(f"/courses/{_COURSE}/diagnostic")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, "one bad skill must not 503 the baseline"
    body = resp.json()
    assert body["questions"] == []
    assert body["status"] == "generating"
    assert len(body["pendingSkillIds"]) == 4
    assert len(body["failedSkillIds"]) == 1


def test_questions_stay_aligned_to_their_skill_when_one_fails(monkeypatch) -> None:
    """map_concurrent_partial returns successes in order but OMITS failures, so
    its length can be shorter than the input. Zip-ing it against the skill list
    would silently mis-align every question after the first failure.

    The failure is deliberately the FIRST skill — the worst case for an
    index-based mapping, where every subsequent question would shift by one.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.deps import get_current_user, CurrentUser

    _diag_harness(monkeypatch, n_skills=5, failing={0})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id="64a59889-ba9c-44ae-87c8-765f86c92c78", app_role="student",
    )
    try:
        with TestClient(app) as client:
            body = client.get(f"/courses/{_COURSE}/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert body["status"] == "generating"
    assert len(body["pendingSkillIds"]) == 4


def test_all_skills_failing_returns_an_empty_sitting_not_an_error(monkeypatch) -> None:
    """The degenerate case: nothing could be generated. An empty list with a
    skipped count is the honest answer; a 5xx is not."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.deps import get_current_user, CurrentUser

    _diag_harness(monkeypatch, n_skills=3, failing={0, 1, 2})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id="64a59889-ba9c-44ae-87c8-765f86c92c78", app_role="student",
    )
    try:
        with TestClient(app) as client:
            resp = client.get(f"/courses/{_COURSE}/diagnostic")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["questions"] == []
    assert resp.json()["status"] == "failed"
    assert len(resp.json()["failedSkillIds"]) == 3


def test_a_healthy_sitting_reports_zero_skipped(monkeypatch) -> None:
    """No regression in the normal path: every skill generates, nothing is
    reported as skipped."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.deps import get_current_user, CurrentUser

    _diag_harness(monkeypatch, n_skills=4, failing=set())
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="00000000-0000-4000-8000-000000000040",
        institution_id="64a59889-ba9c-44ae-87c8-765f86c92c78", app_role="student",
    )
    try:
        with TestClient(app) as client:
            body = client.get(f"/courses/{_COURSE}/diagnostic").json()
    finally:
        app.dependency_overrides.clear()

    assert body["questions"] == []
    assert body["status"] == "generating"
