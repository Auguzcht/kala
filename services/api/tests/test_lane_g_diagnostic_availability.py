"""APPROVAL-06 Lane G: DIAG-REQ-009–011, entirely synthetic and offline."""
from collections import Counter, defaultdict

import pytest
from fastapi.testclient import TestClient

from app.bank import serving
from app.deps import CurrentUser, get_current_user
from app.main import app
from app.routers import diagnostic
from wi26_student_fixtures import enrolled_student_reads

COURSE = "00000000-0000-4000-8000-000000000001"
INSTITUTION = "00000000-0000-4000-8000-000000000050"
USER = "00000000-0000-4000-8000-000000000040"
LEARNER = CurrentUser(user_id=USER, institution_id=INSTITUTION, app_role="student")


class AvailabilityData:
    def __init__(self):
        self.tables = defaultdict(list)
        self.tables["courses"] = [{"id": COURSE, "institution_id": INSTITUTION, "bank_serving": True}]
        self.calls, self.kicks, self.enqueued = [], [], []

    def add(self, number, *, state="ready", items=1, tested=False,
            evidence=None, reviewed=False, module="a"):
        sid = f"00000000-0000-4000-8000-{number:012d}"
        scope = {"institution_id": INSTITUTION, "course_id": COURSE, "skill_id": sid}
        self.tables["skills"].append({**scope, "id": sid, "name": f"Skill {number}",
            "bloom_level": "apply", "status": "approved", "module_ref": module,
            "created_at": f"{number:012d}"})
        if state is not None:
            self.tables["skill_bank_state"].append({**scope, "status": state, "mcq_ready": items})
        for index in range(items):
            iid = f"item-{number:012d}-{index:04d}"
            self.tables["generated_items"].append({**scope, "id": iid, "origin": "bank",
                "kind": "practice", "retired_at": None, "created_at": f"{index:04d}",
                "prompt": "Synthetic question?", "choices": [{"id": "a", "label": "A"}],
                "correct_choice_id": "a", "bloom_level": "apply"})
            if tested:
                self.tables["item_exposures"].append({**scope, "user_id": USER,
                    "item_id": iid, "last_tested_at": "2026-01-01T00:00:00Z"})
        if evidence:
            self.tables["evidence_events"].append({**scope, "id": f"evidence-{number}",
                                                   "user_id": USER, "type": evidence})
        if reviewed:
            self.tables["item_reviews"].append({**scope, "id": f"review-{number}",
                "user_id": USER, "mode": "flashcard", "counted": False})
        return sid

    def select(self, table, params):
        self.calls.append((table, dict(params)))
        rows = list(self.tables[table])
        for key, value in params.items():
            if key in {"select", "order", "limit", "offset"}:
                continue
            if key == "skills.status":
                rows = [r for r in rows if any(s["id"] == r["skill_id"] and
                    s["status"] == "approved" for s in self.tables["skills"])]
            elif value.startswith("eq."):
                rows = [r for r in rows if str(r.get(key)) == value[3:]]
            elif value.startswith("in.("):
                rows = [r for r in rows if r.get(key) in set(value[4:-1].split(","))]
            elif value == "is.null":
                rows = [r for r in rows if r.get(key) is None]
            elif value == "not.is.null":
                rows = [r for r in rows if r.get(key) is not None]
            else:
                raise AssertionError(f"Unexpected synthetic filter: {key}")
        for order in reversed(params.get("order", "").split(",")):
            if order:
                field, direction = order.split(".")
                rows.sort(key=lambda r: str(r.get(field, "")), reverse=direction == "desc")
        offset = int(params.get("offset", 0))
        return rows[offset:offset + int(params.get("limit", 1000))]

    def enqueue(self, *, skill_id, **scope):
        self.enqueued.append(skill_id)
        jobs = [r for r in self.tables["item_generation_jobs"] if r["skill_id"] == skill_id]
        return (jobs[0] if jobs else {"status": "pending"}), not jobs

    def status(self, module=None):
        return diagnostic.get_diagnostic_status(course_id=COURSE, module_ref=module, user=LEARNER)

    def page(self, module=None):
        return diagnostic.get_diagnostic(course_id=COURSE, module_ref=module, user=LEARNER)


@pytest.fixture
def data(monkeypatch):
    fixture = AvailabilityData()
    monkeypatch.setattr(diagnostic.db, "select", enrolled_student_reads(fixture.select))
    monkeypatch.setattr(diagnostic, "kick_bank", lambda *args: fixture.kicks.append(args))
    monkeypatch.setattr(diagnostic, "enqueue_diagnostic", fixture.enqueue)

    def forbidden(*args, **kwargs):
        pytest.fail("Availability must not write learner data or invoke models")

    for name in ("insert", "update", "upsert", "delete", "insert_evidence", "rpc"):
        monkeypatch.setattr(diagnostic.db, name, forbidden)
    monkeypatch.setattr(diagnostic.item_gen, "generate_question", forbidden)
    return fixture


def parity(data):
    status, page = data.status(), data.page()
    assert page["readyCount"] == len(page["questions"]) == min(status["dueSkillCount"], 10)
    assert status["due"] == (status["dueSkillCount"] > 0)
    assert page["waitingForMaterialCount"] == status["waitingForMaterialCount"]
    return status, page


def test_DIAG_REQ_009_011_mixed_availability(data):
    missing = data.add(10, state="no_material", items=0)
    ready = data.add(11)  # One MCQ is sufficient.
    preparing = data.add(12, state="building", items=0)
    exhausted = data.add(13, tested=True)
    practiced = data.add(14, evidence="practice")
    studied = data.add(15, reviewed=True)
    failed = data.add(16, state="error", items=0)
    status, page = parity(data)
    assert status["dueSkillCount"] == status["waitingForMaterialCount"] == 1
    assert page["status"] == "ready"
    assert [q["skillId"] for q in page["questions"]] == [ready]
    assert page["pendingSkillIds"] == [preparing, exhausted]
    assert page["failedSkillIds"] == [failed] and page["skippedSkillCount"] == 1
    assert not {missing, practiced, studied} & set(page["pendingSkillIds"] + page["failedSkillIds"])
    assert all("correct_choice_id" not in q for q in page["questions"])


def test_DIAG_REQ_010_filter_before_ten_uncapped_and_deterministic(data):
    for number in range(10, 22):
        data.add(number, state="no_material", items=0)
    ready = [data.add(number) for number in range(22, 35)]
    status, page = parity(data)
    assert status["dueSkillCount"] == 13 and page["waitingForMaterialCount"] == 12
    assert [q["skillId"] for q in page["questions"]] == ready[:10]
    assert data.page() == page
    counts = Counter(table for table, _ in data.calls)
    assert counts["skill_bank_state"] == counts["generated_items"] == 3
    assert data.kicks == []


@pytest.mark.parametrize("kind", ["diagnostic", "practice", "flashcard", "tutor", "quiz"])
def test_DIAG_REQ_009_any_evidence_type_excludes_skill(data, kind):
    data.add(10, evidence=kind)
    status, page = parity(data)
    assert status["dueSkillCount"] == 0 and page["status"] == "ready"
    assert page["pendingSkillIds"] == page["failedSkillIds"] == []


def test_DIAG_REQ_009_item_review_excludes_without_mastery_evidence(data):
    data.add(10, reviewed=True)
    assert data.tables["evidence_events"] == []
    assert data.status()["dueSkillCount"] == 0


@pytest.mark.parametrize("case", ["empty", "material", "preparing", "exhausted", "failed", "completed"])
def test_DIAG_REQ_011_empty_state_precedence(data, case):
    if case != "empty":
        data.add(10, state={"material": "no_material", "failed": "error"}.get(case, "building"),
                 items=int(case in {"exhausted", "completed"}), tested=case == "exhausted",
                 evidence="diagnostic" if case == "completed" else None)
    status, page = parity(data)
    assert not status["due"]
    assert page["status"] == ("generating" if case in {"preparing", "exhausted"}
                              else "failed" if case == "failed" else "ready")
    assert page["waitingForMaterialCount"] == int(case == "material")
    assert len(page["failedSkillIds"]) == int(case == "failed")


def test_DIAG_REQ_011_pending_precedes_failure_and_material(data):
    pending = data.add(10, items=0, state="building")
    data.add(11, items=0, state="error")
    data.add(12, items=0, state="no_material")
    _, page = parity(data)
    assert page["status"] == "generating" and page["pendingSkillIds"] == [pending]
    assert page["waitingForMaterialCount"] == 1


def test_DIAG_REQ_009_status_has_no_preparation_side_effects(data):
    data.add(10, items=0, state="building")
    data.status()
    data.status()
    assert data.kicks == data.enqueued == []
    data.page()
    assert data.kicks == [(COURSE, "diagnostic")]


@pytest.mark.parametrize("table", ["evidence_events", "item_reviews"])
def test_DIAG_REQ_009_history_after_rest_cap(data, table):
    first, last = data.add(10), data.add(11)
    for index in range(501):
        data.tables[table].append({"id": f"history-{index:05d}",
            "institution_id": INSTITUTION, "course_id": COURSE, "user_id": USER,
            "skill_id": first if index < 500 else last})
    assert data.status()["dueSkillCount"] == 0
    assert any(t == table and p.get("offset") == "500" for t, p in data.calls)


def test_DIAG_REQ_009_tenant_course_learner_module_boundaries(data):
    target = data.add(10)
    data.add(11, module="b")
    for field, wrong in (("institution_id", "other-institution"),
                         ("course_id", "other-course"), ("user_id", "other-learner")):
        for table in ("evidence_events", "item_reviews", "item_exposures"):
            data.tables[table].append({"id": f"foreign-{field}",
                "institution_id": INSTITUTION, "course_id": COURSE, "user_id": USER,
                "skill_id": target, "item_id": data.tables["generated_items"][0]["id"],
                "last_tested_at": "2026-01-01", field: wrong})
    status, page = data.status(module="a"), data.page(module="a")
    assert status["dueSkillCount"] == 1
    assert [q["skillId"] for q in page["questions"]] == [target]
    for table, params in data.calls:
        assert params["institution_id"] == f"eq.{INSTITUTION}"
        if table != "courses":
            assert params["course_id"] == f"eq.{COURSE}"
        if table in {"evidence_events", "item_reviews", "item_exposures"}:
            assert params["user_id"] == f"eq.{USER}"


def test_DIAG_REQ_010_picker_oldest_untested_live_approved_mcq(data):
    sid = data.add(10, items=3)
    pool = data.tables["generated_items"]
    data.tables["item_exposures"].append({"institution_id": INSTITUTION, "course_id": COURSE,
        "user_id": USER, "skill_id": sid, "item_id": pool[0]["id"], "last_tested_at": "2026-01-01"})
    for field, value in (("retired_at", "2026-01-01"), ("origin", "legacy"), ("kind", "flashcard")):
        pool.insert(0, {**pool[-1], "id": f"invalid-{field}", "created_at": "0000", field: value})
    rejected = data.add(11)
    data.tables["skills"][-1]["status"] = "rejected"
    assert serving.pick_diagnostic_item(USER, COURSE, sid, institution_id=INSTITUTION)["id"].endswith("-0001")
    assert serving.pick_diagnostic_item(USER, COURSE, rejected, institution_id=INSTITUTION) is None


def test_DIAG_REQ_010_picker_pool_and_exposure_after_rest_cap(data):
    sid = data.add(10, items=502, tested=True)
    data.tables["item_exposures"].pop()
    assert serving.pick_diagnostic_item(USER, COURSE, sid, institution_id=INSTITUTION)["id"].endswith("-0501")
    for table in ("generated_items", "item_exposures"):
        assert any(t == table and p.get("offset") == "500" for t, p in data.calls)


def test_DIAG_REQ_010_multiple_skill_batches(data):
    for number in range(10, 112):
        data.add(number)
    status, page = parity(data)
    assert status["dueSkillCount"] == 102 and page["readyCount"] == 10


def test_DIAG_REQ_011_legacy_saved_items_and_truthful_worker_states(data):
    data.tables["courses"][0]["bank_serving"] = False
    ready = data.add(10, state=None)
    pending = data.add(11, state=None, items=0)
    missing = data.add(12, state=None, items=0)
    failed = data.add(13, state=None, items=0)
    data.tables["generated_items"][0]["kind"] = "diagnostic"
    for sid, error in ((missing, "NoCourseContentError"), (failed, "ModelUnavailableError")):
        data.tables["item_generation_jobs"].append({"id": f"job-{sid}",
            "institution_id": INSTITUTION, "course_id": COURSE, "skill_id": sid,
            "kind": "diagnostic", "status": "failed", "last_error": error})
    status, page = parity(data)
    assert status["dueSkillCount"] == 1 and page["status"] == "ready"
    assert [q["skillId"] for q in page["questions"]] == [ready]
    assert page["pendingSkillIds"] == [pending] and page["failedSkillIds"] == [failed]
    assert page["waitingForMaterialCount"] == 1


def test_DIAG_REQ_010_legacy_ready_after_ten_unavailable(data):
    data.tables["courses"][0]["bank_serving"] = False
    for number in range(10, 22):
        data.add(number, state="no_material", items=0)
    ready = data.add(22, state=None)
    data.tables["generated_items"][0]["kind"] = "diagnostic"
    status, page = parity(data)
    assert status["dueSkillCount"] == 1
    assert [q["skillId"] for q in page["questions"]] == [ready]
    assert data.enqueued == []


def test_DIAG_REQ_009_011_http_workspace_page_parity(data):
    data.add(10)
    data.add(11, state="no_material", items=0)
    app.dependency_overrides[get_current_user] = lambda: LEARNER
    try:
        with TestClient(app) as client:
            status = client.get(f"/courses/{COURSE}/diagnostic/status").json()
            page = client.get(f"/courses/{COURSE}/diagnostic").json()
    finally:
        app.dependency_overrides.clear()
    assert status["dueSkillCount"] == page["readyCount"] == 1
    assert status["waitingForMaterialCount"] == page["waitingForMaterialCount"] == 1


def test_DIAG_REQ_009_011_completed_sitting_clears_notice(data, monkeypatch):
    sid = data.add(10)
    item = data.tables["generated_items"][0]
    assert data.status()["due"]
    monkeypatch.setattr(diagnostic.item_gen, "grade", lambda **kwargs: {
        "skillId": sid, "courseId": COURSE, "correct": True, "explanation": "Synthetic"})
    monkeypatch.setattr(diagnostic, "record_exposure", lambda **kwargs: None)
    monkeypatch.setattr(diagnostic.db, "insert_evidence", lambda rows: data.tables["evidence_events"].extend(
        [{**row, "id": "submitted-evidence"} for row in rows]))
    monkeypatch.setattr(diagnostic.tracer, "apply_evidence", lambda **kwargs: {"estimate": 0.6})
    diagnostic.submit_diagnostic(
        diagnostic.SubmitBody(answers=[diagnostic.SubmitAnswer(item_id=item["id"], choice_id="a")]),
        course_id=COURSE, user=LEARNER)
    status, page = parity(data)
    assert not status["due"] and page["status"] == "ready" and page["questions"] == []
    assert len(data.tables["evidence_events"]) == 1


def test_DIAG_REQ_009_legacy_status_never_enqueues(data):
    data.tables["courses"][0]["bank_serving"] = False
    data.add(10, state=None, items=0)
    data.status()
    data.status()
    assert data.enqueued == data.kicks == []


def test_DIAG_REQ_010_skill_list_after_rest_cap(data):
    for number in range(100, 601):
        data.add(number, items=0, state="no_material")
    data.add(601)
    status, page = parity(data)
    assert status["dueSkillCount"] == page["readyCount"] == 1
    assert page["waitingForMaterialCount"] == 501
    assert any(t == "skills" and p.get("offset") == "500" for t, p in data.calls)


def test_DIAG_REQ_011_recorded_failure_precedes_material_only(data):
    data.add(10, state="no_material", items=0)
    failed = data.add(11, state="error", items=0)
    _, page = parity(data)
    assert page["status"] == "failed"
    assert page["failedSkillIds"] == [failed]
    assert page["waitingForMaterialCount"] == 1


def test_DIAG_REQ_010_legacy_worker_completion_race(data, monkeypatch):
    data.tables["courses"][0]["bank_serving"] = False
    sid = data.add(10, state=None, items=0)

    def enqueue(**kwargs):
        data.tables["generated_items"].append({
            "id": "completed-item", "institution_id": INSTITUTION, "course_id": COURSE,
            "skill_id": sid, "kind": "diagnostic", "retired_at": None,
            "prompt": "Synthetic completed question?", "choices": [],
        })
        return {"status": "pending"}, True

    monkeypatch.setattr(diagnostic, "enqueue_diagnostic", enqueue)
    page = data.page()
    assert page["status"] == "ready" and page["readyCount"] == 1
    assert page["pendingSkillIds"] == page["failedSkillIds"] == []


def test_DIAG_REQ_010_legacy_material_jobs_do_not_block_preparation(data):
    data.tables["courses"][0]["bank_serving"] = False
    for number in range(10, 22):
        sid = data.add(number, state=None, items=0)
        data.tables["item_generation_jobs"].append({
            "id": f"job-{number}", "institution_id": INSTITUTION, "course_id": COURSE,
            "skill_id": sid, "kind": "diagnostic", "status": "failed",
            "last_error": "NoCourseContentError",
        })
    pending = data.add(22, state=None, items=0)
    page = data.page()
    assert data.enqueued == [pending]
    assert page["pendingSkillIds"] == [pending]
    assert page["waitingForMaterialCount"] == 12
    assert page["failedSkillIds"] == []
