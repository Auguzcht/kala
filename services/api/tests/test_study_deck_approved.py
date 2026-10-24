"""APPROVAL-01 Study regressions; all database calls stay in memory."""
from datetime import datetime, timezone

import pytest
from app.bank import serving
from app.deps import CurrentUser, get_current_user
from app.learn import srs
from app.routers import flashcards
from fastapi import FastAPI
from fastapi.testclient import TestClient

COURSE = "00000000-0000-4000-8000-000000000001"
SKILL = "00000000-0000-4000-8000-000000000010"
USER = CurrentUser(user_id="student", institution_id="institution", app_role="student")


@pytest.fixture
def study(monkeypatch):
    class Store:
        def __init__(self):
            self.schedules = []
            self.mutations = []
            self.selections = []
            self.items = [
                {"id": "fresh", "skill_id": SKILL, "kind": "practice", "origin": "bank",
                 "prompt": "Fresh question", "choices": [{"id": "a", "label": "Fresh answer"}],
                 "correct_choice_id": "a", "retired_at": None, "status": "approved"},
                {"id": "flip", "skill_id": SKILL, "kind": "flashcard", "origin": "bank",
                 "prompt": "Fallback prompt", "front": "Native front", "back": "Native back",
                 "choices": [], "retired_at": None, "status": "approved"},
            ]

        def select(self, table, params):
            self.selections.append((table, params))
            if table == "skills":
                return [{"id": SKILL, "name": "Skill", "module_ref": "module"}]
            if table == "courses":
                return [{"id": COURSE, "bank_serving": True}]
            if table == "institutions":
                return [{"timezone": "UTC"}]
            if table == "skill_bank_state":
                return [{"status": "ready", "mcq_ready": len(self.items)}]
            if table == "item_exposures":
                return []
            if table == "srs_state":
                rows = list(self.schedules)
                if params.get("reps") == "eq.0":
                    rows = [row for row in rows if row["reps"] == 0]
                if params.get("daily_new_claimed"):
                    rows = [row for row in rows if row["daily_new_claimed"]]
                if params.get("due_at"):
                    rows = [row for row in rows if row["due_at"] <= params["due_at"][4:]]
                return rows
            if table == "generated_items":
                rows = [item for item in self.items if item["retired_at"] is None and item["status"] == "approved"]
                if params.get("id", "").startswith("in.("):
                    ids = params["id"][4:-1].split(",")
                    rows = [item for item in rows if item["id"] in ids]
                if params.get("kind") == "eq.practice":
                    rows = [item for item in rows if item["kind"] == "practice"]
                return rows
            raise AssertionError(table)

        def write(self, *args, **kwargs):
            self.mutations.append((args, kwargs))
            raise AssertionError("unexpected mutation outside a fresh claim")

        def claim(self, name, args):
            assert name == "claim_study_cards"
            self.mutations.append((name, args))
            result = []
            for item_id in args["p_item_ids"]:
                existing = any(row["item_id"] == item_id for row in self.schedules)
                if not existing:
                    self.add_schedule(item_id)
                result.append({"item_id": item_id, "is_new": not existing})
            return result

        def add_schedule(self, item_id, *, reps=0, due_at="2020-01-01T00:00:00+00:00"):
            self.schedules.append({
                "item_id": item_id, "skill_id": SKILL, "box": 0, "streak": 0,
                "reps": reps, "ease_milli": 2500, "lapses": 0,
                "due_at": due_at, "last_outcome": "good" if reps else None,
                "daily_new_claimed": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    store = Store()
    monkeypatch.setattr(flashcards.db, "select", store.select)
    for method in ("insert", "upsert", "update", "delete"):
        monkeypatch.setattr(flashcards.db, method, store.write)
    monkeypatch.setattr(flashcards.db, "rpc", store.claim)
    # These must be unreachable for counts or already claimed cards.
    monkeypatch.setattr(flashcards, "record_exposure", store.write)
    monkeypatch.setattr(srs, "ensure_tracked", store.write)
    app = FastAPI()
    app.include_router(flashcards.router)
    app.dependency_overrides[get_current_user] = lambda: USER
    with TestClient(app) as client:
        yield store, client


@pytest.mark.parametrize("mode", [None, "review", "all"])
@pytest.mark.parametrize("preclaimed", [False, True])
def test_STUDY_REQ_001_counts_twice_never_claims_or_spends(study, mode, preclaimed):
    store, client = study
    if preclaimed:
        store.add_schedule("flip")
    expected_remaining = 19 if preclaimed else 20
    before = list(store.schedules)
    suffix = f"&mode={mode}" if mode else ""
    for _ in range(2):
        response = client.get(f"/flashcards/{COURSE}/deck?limit=0{suffix}")
        assert response.status_code == 200
        assert response.json()["cards"] == []
        assert response.json()["stats"]["tracked"] == len(before)
        assert response.json()["newRemainingToday"] == expected_remaining
    assert store.schedules == before
    assert store.mutations == []
    assert srs.new_remaining_today(institution_id=USER.institution_id, user_id=USER.user_id,
                                   course_id=COURSE) == expected_remaining


@pytest.mark.parametrize("item_id", ["fresh", "flip"])
def test_STUDY_REQ_002_unrated_is_resumed_without_claim_or_cap_spend(study, item_id):
    store, client = study
    store.add_schedule(item_id)
    for _ in range(2):
        response = client.get(f"/flashcards/{COURSE}/deck?mode=review&limit=1")
        assert response.status_code == 200
        body = response.json()
        assert [card["itemId"] for card in body["cards"]] == [item_id]
        assert body["cards"][0]["state"] == "new"
        assert body["newRemainingToday"] == 19
        if item_id == "flip":
            assert body["cards"][0]["prompt"] == "Native front"
            assert body["cards"][0]["back"]["label"] == "Native back"
    assert store.mutations == []
    assert len(store.schedules) == 1


def test_STUDY_REQ_002_unrated_still_serves_at_cap(study):
    store, client = study
    for number in range(19):
        store.add_schedule(f"retired-{number}", reps=1)
    store.add_schedule("flip")
    response = client.get(f"/flashcards/{COURSE}/deck?mode=review&limit=20")
    assert response.status_code == 200
    assert [card["itemId"] for card in response.json()["cards"]] == ["flip"]
    assert response.json()["newRemainingToday"] == 0
    assert store.mutations == []


def test_STUDY_REQ_002_due_then_unrated_then_fresh_top_up(study, monkeypatch):
    store, client = study
    store.items.append({**store.items[0], "id": "due"})
    store.add_schedule("due", reps=1)
    store.add_schedule("flip")
    writes = []
    monkeypatch.setattr(flashcards, "record_exposure", lambda **kw: writes.append(("exposure", kw)))
    monkeypatch.setattr(srs, "ensure_tracked", lambda **kw: writes.append(("track", kw)))
    response = client.get(f"/flashcards/{COURSE}/deck?mode=review&limit=3")
    assert response.status_code == 200
    body = response.json()
    assert [card["itemId"] for card in body["cards"]] == ["due", "flip", "fresh"]
    assert body["newRemainingToday"] == 17  # only the one fresh card spends a slot
    assert store.mutations[0][1]["p_item_ids"] == ["fresh"]
    assert len(store.schedules) == 3
    assert all(kw["item_id"] == "fresh" for _, kw in writes)


def test_STUDY_REQ_002_unrated_excludes_retired_and_rejected(study):
    store, client = study
    store.items[0]["retired_at"] = "2026-01-01T00:00:00Z"
    store.items[1]["status"] = "rejected"
    store.add_schedule("fresh")
    store.add_schedule("flip")
    response = client.get(f"/flashcards/{COURSE}/deck?mode=review")
    assert response.status_code == 200
    assert response.json()["cards"] == []
    assert store.mutations == []


def test_STUDY_REQ_002_shared_due_and_test_pools_keep_original_behavior(study):
    store, _ = study
    store.add_schedule("fresh")
    store.add_schedule("flip")
    assert srs.due_cards(institution_id=USER.institution_id, user_id=USER.user_id,
                         course_id=COURSE) == []
    selected, _ = serving.pick_bank_items_with_meta(USER.user_id, COURSE, SKILL, 20, "test",
                                                   institution_id=USER.institution_id)
    assert [item["id"] for item in selected] == ["fresh"]
    params = [params for table, params in store.selections if table == "generated_items"][-1]
    assert params["origin"] == "eq.bank"
    assert params["kind"] == "eq.practice"
    assert "front" not in params["select"]


def test_STUDY_REQ_002_study_fresh_pool_includes_native_flip_cards(study):
    _, _client = study
    selected = serving.pick_bank_items(USER.user_id, COURSE, SKILL, 20, "study",
                                       institution_id=USER.institution_id)
    assert {item["id"] for item in selected} == {"fresh", "flip"}
