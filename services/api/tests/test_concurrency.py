import time

from app.ai.concurrency import map_concurrent


def test_preserves_input_order_regardless_of_completion_order():
    """Item 0 finishes last, item 2 finishes first — the RETURNED list must
    still be in input order, not completion order."""
    def slow_if_first(i: int) -> int:
        if i == 0:
            time.sleep(0.05)
        return i * 10

    out = map_concurrent(slow_if_first, [0, 1, 2])
    assert out == [0, 10, 20]


def test_empty_input_short_circuits_without_a_pool():
    assert map_concurrent(lambda x: 1 / 0, []) == []


def test_exception_propagates_same_as_a_plain_comprehension():
    """Semantics must match `[fn(i) for i in items]`: a failure surfaces,
    it is never silently dropped from the batch."""
    def boom(i: int) -> int:
        if i == 1:
            raise ValueError("bad item")
        return i

    try:
        map_concurrent(boom, [0, 1, 2])
        assert False, "expected ValueError to propagate"
    except ValueError as exc:
        assert str(exc) == "bad item"


def test_actually_runs_concurrently_not_serially():
    """The whole point: N items that each sleep for T seconds must take
    roughly T seconds total, not N*T. This is the actual fix for the
    multi-minute diagnostic/flashcard/lesson generation waits."""
    n = 5
    per_item_seconds = 0.15

    def slow(_i: int) -> int:
        time.sleep(per_item_seconds)
        return _i

    started = time.monotonic()
    out = map_concurrent(slow, list(range(n)), max_workers=n)
    elapsed = time.monotonic() - started

    assert out == list(range(n))
    # Serial would take n * per_item_seconds (~0.75s); concurrent should be
    # close to one item's time. Generous ceiling to avoid CI flakiness.
    assert elapsed < per_item_seconds * (n / 2)


def test_respects_max_workers_ceiling():
    """max_workers caps concurrency even with more items than workers —
    correctness (order, completion) must still hold."""
    out = map_concurrent(lambda i: i + 1, list(range(10)), max_workers=2)
    assert out == list(range(1, 11))
