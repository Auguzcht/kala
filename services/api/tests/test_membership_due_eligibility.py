"""Membership due badges and Review due must describe the same cards."""
from datetime import datetime, timezone

import pytest

from app.deps import CurrentUser
from app.learn import srs
from app.routers import flashcards


NOW = datetime(2026, 10, 18, 4, tzinfo=timezone.utc)
USER = CurrentUser(user_id="student", institution_id="institution", app_role="student")


@pytest.fixture
def membership_data(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)

    items = [{
        "id": item_id, "skill_id": "skill", "kind": "practice", "origin": "bank",
        "prompt": item_id, "choices": [{"id": "a", "label": "Answer"}],
        "correct_choice_id": "a",
    } for item_id in ("graduated", "known", "future", "new-tracked", "new-untracked")]
    schedules = [{
        "item_id": item_id, "skill_id": "skill", "box": box, "streak": streak,
        "reps": reps, "ease_milli": 2500, "lapses": 0,
        "last_outcome": "good" if reps else None, "due_at": due_at,
    } for item_id, box, streak, reps, due_at in (
        ("graduated", 5, 3, 4, "2026-10-17T00:00:00Z"),
        ("known", 4, 2, 2, "2026-10-17T01:00:00Z"),
        ("future", 4, 2, 2, "2026-10-19T00:00:00Z"),
        ("new-tracked", 0, 0, 0, "2026-10-17T00:00:00Z"),
    )]

    def select(table, params):
        if table == "skills":
            return [{"id": "skill", "name": "Skill"}]
        if table == "generated_items":
            return items
        if table == "srs_state":
            return schedules
        if table == "institutions":
            return [{"timezone": "Asia/Manila"}]
        if table == "courses":
            return [{"id": "course", "bank_serving": True}]
        if table == "skill_bank_state":
            return [{"status": "ready", "mcq_ready": len(items)}]
        raise AssertionError(table)

    def no_writes(*args, **kwargs):
        pytest.fail("membership and existing due-card selection must not write")

    monkeypatch.setattr(flashcards.db, "select", select)
    monkeypatch.setattr(flashcards.db, "insert", no_writes)
    monkeypatch.setattr(flashcards.db, "update", no_writes)
    monkeypatch.setattr(flashcards.db, "rpc", no_writes)
    monkeypatch.setattr(flashcards, "datetime", FixedDatetime)
    monkeypatch.setattr(srs, "_now", lambda: NOW)
    # Exhausting the new-card allowance must not restrict existing due cards.
    monkeypatch.setattr(flashcards, "_new_cards_remaining", lambda **kwargs: 0)
    return items, schedules


@pytest.mark.parametrize("item_id,expected_due,expected_state", [
    ("graduated", False, "known"),
    ("known", True, "known"),
    ("future", False, "known"),
    ("new-tracked", False, "new"),
    ("new-untracked", False, "new"),
])
def test_membership_due_eligibility(membership_data, item_id, expected_due, expected_state):
    items, schedules = membership_data
    items[:] = [item for item in items if item["id"] == item_id]
    schedules[:] = [row for row in schedules if row["item_id"] == item_id]

    result = flashcards.skill_cards(course_id="course", skill_id="skill", user=USER)

    assert len(result["cards"]) == 1  # Graduation never removes browse membership.
    card = result["cards"][0]
    assert card["itemId"] == item_id
    assert card["state"] == expected_state
    assert card["due"] is expected_due
    assert result["counts"]["dueToday"] == int(expected_due)
    assert set(result) == {"skillId", "counts", "cards"}
    assert set(card) == {"itemId", "prompt", "back", "state", "due", "dueAt"}


def test_STUDY_REQ_002_review_adds_unrated_without_changing_membership_due(membership_data):
    membership = flashcards.skill_cards(course_id="course", skill_id="skill", user=USER)
    selected = srs.due_cards(
        institution_id=USER.institution_id, user_id=USER.user_id,
        course_id="course", skill_id="skill", limit=1000,
    )
    review = flashcards.deck(
        course_id="course", skill_id="skill", user=USER,
        mode="review", limit=20, offset=0, module_ref=None,
    )

    due_ids = {card["itemId"] for card in membership["cards"] if card["due"]}
    assert due_ids == {row["item_id"] for row in selected} == {"known"}
    assert {card["itemId"] for card in review["cards"]} == due_ids | {"new-tracked"}
    assert membership["counts"]["dueToday"] == len(selected) == 1
    assert review["newRemainingToday"] == 0
    assert len(membership["cards"]) == 5


def test_due_today_includes_later_today_but_excludes_local_midnight(membership_data):
    items, schedules = membership_data
    items[:] = [item for item in items if item["id"] in {"known", "future"}]
    schedules[:] = [row for row in schedules if row["item_id"] in {"known", "future"}]
    schedules[0]["due_at"] = "2026-10-18T15:59:59Z"  # 23:59:59 Manila
    schedules[1]["due_at"] = "2026-10-18T16:00:00Z"  # tomorrow at midnight

    result = flashcards.skill_cards(course_id="course", skill_id="skill", user=USER)

    assert all(not card["due"] for card in result["cards"])
    assert result["counts"]["dueToday"] == 1
