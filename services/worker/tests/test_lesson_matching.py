from app.lesson_matching import assign_matches


def vec(x, y=0):
    return [x, y] + [0.0] * 1022


def test_best_similarity_wins_and_duplicate_candidates_are_excluded():
    steps = [{"id": "s1", "embedding": vec(1, 0)}, {"id": "s2", "embedding": vec(0, 1)}]
    items = [
        {"id": "best", "embedding": vec(1, 0)},
        {"id": "duplicate", "embedding": vec(0.999, 0.001)},
        {"id": "other", "embedding": vec(0, 1)},
    ]
    matches = assign_matches(steps, items)
    assert matches["s1"][0] == "best"
    assert matches["s2"][0] == "other"
    assert "duplicate" not in {item_id for item_id, _ in matches.values()}


def test_bloom_level_bonus_breaks_a_similarity_tie():
    steps = [{"id": "s", "embedding": vec(1), "bloom_level": "apply"}]
    items = [
        {"id": "same-bloom", "embedding": vec(1), "bloom_level": "apply"},
        {"id": "other-bloom", "embedding": vec(1), "bloom_level": "remember"},
    ]
    assert assign_matches(steps, items)["s"][0] == "same-bloom"


def test_minimum_score_floor_leaves_step_unassigned():
    steps = [{"id": "s", "embedding": vec(1, 0)}]
    items = [{"id": "weak", "embedding": vec(0.1, 0.995)}]
    assert assign_matches(steps, items) == {}


def test_existing_assignment_is_preserved_and_its_duplicates_removed():
    steps = [
        {"id": "done", "embedding": vec(1, 0), "check_item_id": "assigned"},
        {"id": "open", "embedding": vec(0, 1)},
    ]
    items = [
        {"id": "assigned", "embedding": vec(1, 0)},
        {"id": "duplicate", "embedding": vec(0.999, 0.001)},
        {"id": "available", "embedding": vec(0, 1)},
    ]
    assert assign_matches(steps, items)["open"][0] == "available"
