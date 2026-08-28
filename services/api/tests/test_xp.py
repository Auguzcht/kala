"""XP derivation tests. Everything is a pure function of the evidence log and
mastery state, so these confirm the reward view stays consistent with the twin
and cannot be inflated by activity alone."""
from datetime import datetime, timedelta, timezone

from app.learn import xp


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_xp_rewards_correct_over_attempts(monkeypatch):
    now = datetime.now(timezone.utc)
    events = [
        {"correct": True, "created_at": _iso(now)},
        {"correct": False, "created_at": _iso(now)},
        {"correct": True, "created_at": _iso(now)},
    ]
    monkeypatch.setattr(xp.db, "select", lambda table, params:
                        events if table == "evidence_events" else [])
    out = xp.summary(institution_id="inst-1", user_id="u-1", course_id="c-1")
    # 2 correct * 10 + 3 attempts * 2 = 26
    assert out["xp"] == 26
    assert out["attempts"] == 3
    assert out["correct"] == 2


def test_streak_counts_consecutive_days_up_to_today():
    now = datetime.now(timezone.utc)
    created = [
        _iso(now),
        _iso(now - timedelta(days=1)),
        _iso(now - timedelta(days=2)),
        _iso(now - timedelta(days=5)),  # gap breaks it
    ]
    assert xp._streak_days(created) == 3


def test_streak_survives_an_unfinished_today():
    now = datetime.now(timezone.utc)
    created = [
        _iso(now - timedelta(days=1)),
        _iso(now - timedelta(days=2)),
    ]
    # No event today yet, but yesterday+before form a live 2-day streak.
    assert xp._streak_days(created) == 2


def test_streak_zero_when_no_recent_activity():
    old = datetime.now(timezone.utc) - timedelta(days=10)
    assert xp._streak_days([_iso(old)]) == 0


def test_streak_empty():
    assert xp._streak_days([]) == 0


def test_badges_award_skill_and_bloom_tiers(monkeypatch):
    skills = [
        {"id": "s1", "name": "Truth tables", "bloom_level": "apply"},
        {"id": "s2", "name": "Karnaugh maps", "bloom_level": "apply"},
        {"id": "s3", "name": "Gate types", "bloom_level": "remember"},
    ]
    mastery = [
        {"skill_id": "s1", "estimate": 0.9},   # mastered
        {"skill_id": "s2", "estimate": 0.75},  # proficient
        {"skill_id": "s3", "estimate": 0.4},   # neither
    ]

    def fake_select(table, params):
        if table == "skills":
            return skills
        if table == "mastery_state":
            return mastery
        return []

    monkeypatch.setattr(xp.db, "select", fake_select)
    badges = xp._badges(institution_id="inst-1", user_id="u-1", course_id="c-1")

    tiers = {(b["kind"], b["label"]): b["tier"] for b in badges}
    assert tiers[("skill", "Truth tables")] == "mastered"
    assert tiers[("skill", "Karnaugh maps")] == "proficient"
    # 'apply' bloom badge earned: both apply skills are proficient-or-better.
    assert ("bloom", "apply") in tiers
    # 'remember' bloom badge NOT earned: s3 is below proficient.
    assert ("bloom", "remember") not in tiers
