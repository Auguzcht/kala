"""SRS scheduler tests. The scheduling transition is pure math and carries the
risk, so it is exercised directly; the persistence wrappers are checked with a
monkeypatched db to confirm they read prior state and never reset progress."""
from app.learn import srs
from app.learn.srs import CardState


def _fresh() -> CardState:
    return CardState(box=0, ease_milli=2500, streak=0, reps=0, lapses=0)


# ---- pure transition math -------------------------------------------------

def test_correct_promotes_box_and_grows_streak_and_reps():
    out = srs.schedule_after(_fresh(), correct=True)
    assert out.box == 1
    assert out.streak == 1
    assert out.reps == 1
    assert out.lapses == 0
    assert out.ease_milli > 2500  # nudged up
    assert out.interval_hours > 0


def test_incorrect_resets_box_and_streak_and_records_a_lapse():
    # Start from a partly-learned card, then miss it.
    learned = CardState(box=3, ease_milli=2500, streak=3, reps=5, lapses=0)
    out = srs.schedule_after(learned, correct=False)
    assert out.box == 0            # back to most-frequent box
    assert out.streak == 0         # streak broken
    assert out.lapses == 1         # forgetting recorded (feeds the curve)
    assert out.reps == 6           # still counts as a review
    assert out.ease_milli < 2500   # ease penalised


def test_box_caps_at_max():
    state = CardState(box=5, ease_milli=2500, streak=5, reps=20, lapses=0)
    assert srs.schedule_after(state, correct=True).box == 5


def test_ease_clamps_within_bounds():
    high = CardState(box=2, ease_milli=2990, streak=2, reps=3, lapses=0)
    assert srs.schedule_after(high, correct=True).ease_milli <= 3000
    low = CardState(box=0, ease_milli=1400, streak=0, reps=8, lapses=4)
    assert srs.schedule_after(low, correct=False).ease_milli >= 1300


def test_interval_grows_with_box():
    # A card recalled twice in a row should be due further out each time.
    first = srs.schedule_after(_fresh(), correct=True)
    second = srs.schedule_after(
        CardState(box=first.box, ease_milli=first.ease_milli, streak=first.streak,
                  reps=first.reps, lapses=first.lapses),
        correct=True,
    )
    assert second.interval_hours > first.interval_hours


def test_graduation_requires_top_box_and_streak():
    # One correct at the top box is not enough; the streak gate must be met.
    near = CardState(box=5, ease_milli=2500, streak=srs.GRADUATE_STREAK - 2, reps=9, lapses=0)
    assert srs.schedule_after(near, correct=True).graduated is False
    at = CardState(box=5, ease_milli=2500, streak=srs.GRADUATE_STREAK - 1, reps=9, lapses=0)
    assert srs.schedule_after(at, correct=True).graduated is True


def test_is_mastered_predicate_matches_transition():
    assert srs.is_mastered(box=5, streak=srs.GRADUATE_STREAK) is True
    assert srs.is_mastered(box=5, streak=srs.GRADUATE_STREAK - 1) is False
    assert srs.is_mastered(box=4, streak=10) is False


# ---- persistence wrappers -------------------------------------------------

def test_review_reads_prior_state_then_persists_next_due(monkeypatch):
    captured = {}
    monkeypatch.setattr(srs.db, "select", lambda table, params: [
        {"box": 2, "ease_milli": 2500, "streak": 2, "reps": 4, "lapses": 0},
    ])
    monkeypatch.setattr(srs.db, "upsert",
                        lambda table, rows, on_conflict: captured.update(rows[0]) or rows)

    result = srs.review(
        institution_id="inst-1", user_id="u-1", course_id="c-1",
        item_id="item-1", skill_id="s-1", correct=True,
    )
    assert result.box == 3                      # promoted from the read state
    assert captured["box"] == 3                 # persisted
    assert "due_at" in captured                 # next due time written
    assert "last_reviewed_at" in captured       # review timestamp stamped


def test_review_starts_from_default_when_no_row_exists(monkeypatch):
    monkeypatch.setattr(srs.db, "select", lambda table, params: [])
    monkeypatch.setattr(srs.db, "upsert", lambda table, rows, on_conflict: rows)
    result = srs.review(
        institution_id="inst-1", user_id="u-1", course_id="c-1",
        item_id="new-item", skill_id="s-1", correct=True,
    )
    assert result.box == 1
    assert result.reps == 1


def test_ensure_tracked_does_not_overwrite_existing_progress(monkeypatch):
    """Re-showing a card must never reset its schedule. ensure_tracked selects
    first and only inserts when absent."""
    inserted = []
    monkeypatch.setattr(srs.db, "select", lambda table, params: [{"item_id": "item-1"}])
    monkeypatch.setattr(srs.db, "insert",
                        lambda table, rows, prefer="return=representation": inserted.extend(rows))
    srs.ensure_tracked(
        institution_id="inst-1", user_id="u-1", course_id="c-1",
        item_id="item-1", skill_id="s-1",
    )
    assert inserted == []  # existing row left untouched


def test_ensure_tracked_inserts_when_absent(monkeypatch):
    inserted = []
    monkeypatch.setattr(srs.db, "select", lambda table, params: [])
    monkeypatch.setattr(srs.db, "insert",
                        lambda table, rows, prefer="return=representation": inserted.extend(rows))
    srs.ensure_tracked(
        institution_id="inst-1", user_id="u-1", course_id="c-1",
        item_id="item-2", skill_id="s-1", module_ref="Module 1",
    )
    assert len(inserted) == 1
    assert inserted[0]["item_id"] == "item-2"
    assert inserted[0]["module_ref"] == "Module 1"


def test_due_cards_excludes_mastered(monkeypatch):
    monkeypatch.setattr(srs.db, "select", lambda table, params: [
        {"item_id": "a", "skill_id": "s1", "box": 5, "streak": 5, "due_at": "2020-01-01T00:00:00+00:00"},
        {"item_id": "b", "skill_id": "s2", "box": 1, "streak": 0, "due_at": "2020-01-01T00:00:00+00:00"},
    ])
    out = srs.due_cards(institution_id="inst-1", user_id="u-1", course_id="c-1", limit=10)
    ids = [c["item_id"] for c in out]
    assert ids == ["b"]  # the mastered card 'a' is filtered out
