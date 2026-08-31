from app.jobs import reconcile_mastery


def _fake_evidence(*, correct_sequence, user_id="user-1", skill_id="skill-1", course_id="course-1"):
    return [
        {
            "user_id": user_id, "course_id": course_id, "skill_id": skill_id,
            "correct": c, "created_at": f"2026-01-0{i + 1}T00:00:00Z",
        }
        for i, c in enumerate(correct_sequence)
    ]


def test_no_stale_state_produces_zero_corrections_and_no_upsert(monkeypatch) -> None:
    """mastery_state already matches what replaying evidence_events would
    produce -> nothing to correct, and db.upsert must not be called at all
    (not called with an empty list, not called)."""
    events = _fake_evidence(correct_sequence=[True, True])
    # Replay by hand: 0.5 -> 0.5 + 0.15*(1-0.5) = 0.575 -> 0.575 + 0.15*(1-0.575) = 0.63875
    expected_estimate = round(0.575 + 0.15 * (1 - 0.575), 6)

    upsert_calls = []

    def fake_select(table, params):
        if table == "institutions":
            return [{"id": "inst-1"}]
        if table == "evidence_events":
            return events
        if table == "mastery_state":
            return [{"user_id": "user-1", "skill_id": "skill-1",
                      "estimate": expected_estimate, "attempts": 2}]
        raise AssertionError(f"unexpected select on {table}")

    def fake_upsert(table, rows, *, on_conflict):
        upsert_calls.append((table, rows, on_conflict))
        return rows

    monkeypatch.setattr(reconcile_mastery.db, "select", fake_select)
    monkeypatch.setattr(reconcile_mastery.db, "upsert", fake_upsert)

    result = reconcile_mastery.run()

    assert result == {"pairsChecked": 1, "pairsCorrected": 0}
    assert upsert_calls == []


def test_stale_state_gets_recomputed_and_upserted(monkeypatch) -> None:
    """mastery_state disagrees with what the evidence log implies (simulating
    a request that wrote evidence but never reached the tracer update) ->
    exactly one correction, upserted with the replayed estimate."""
    events = _fake_evidence(correct_sequence=[True, True])
    expected_estimate = round(0.575 + 0.15 * (1 - 0.575), 6)

    upsert_calls = []

    def fake_select(table, params):
        if table == "institutions":
            return [{"id": "inst-1"}]
        if table == "evidence_events":
            return events
        if table == "mastery_state":
            # Stale: stuck at the value after only the FIRST event, as if the
            # second answer's tracer update never landed.
            return [{"user_id": "user-1", "skill_id": "skill-1",
                      "estimate": 0.575, "attempts": 1}]
        raise AssertionError(f"unexpected select on {table}")

    def fake_upsert(table, rows, *, on_conflict):
        upsert_calls.append((table, rows, on_conflict))
        return rows

    monkeypatch.setattr(reconcile_mastery.db, "select", fake_select)
    monkeypatch.setattr(reconcile_mastery.db, "upsert", fake_upsert)

    result = reconcile_mastery.run()

    assert result == {"pairsChecked": 1, "pairsCorrected": 1}
    assert len(upsert_calls) == 1
    table, rows, on_conflict = upsert_calls[0]
    assert table == "mastery_state"
    assert on_conflict == "user_id,skill_id"
    assert rows == [{
        "institution_id": "inst-1", "user_id": "user-1", "course_id": "course-1",
        "skill_id": "skill-1", "estimate": expected_estimate, "attempts": 2,
        "last_seen": events[-1]["created_at"],
    }]


def test_evidence_with_no_skill_id_is_excluded(monkeypatch) -> None:
    """An evidence_events row with a null skill_id (allowed by the schema)
    can't roll up to any mastery_state row, and must be excluded rather than
    crashing on a missing dict key."""
    events = [
        {"user_id": "user-1", "course_id": "course-1", "skill_id": None,
         "correct": True, "created_at": "2026-01-01T00:00:00Z"},
    ]

    def fake_select(table, params):
        if table == "institutions":
            return [{"id": "inst-1"}]
        if table == "evidence_events":
            return events
        if table == "mastery_state":
            return []
        raise AssertionError(f"unexpected select on {table}")

    monkeypatch.setattr(reconcile_mastery.db, "select", fake_select)
    monkeypatch.setattr(
        reconcile_mastery.db, "upsert",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("upsert should not be called")),
    )

    result = reconcile_mastery.run()

    assert result == {"pairsChecked": 0, "pairsCorrected": 0}


def test_institution_id_scopes_to_a_single_institution(monkeypatch) -> None:
    """Passing institution_id must skip the institutions-listing select
    entirely and scope straight to that one institution (the rehearsal /
    manual-invoke path from a Lambda console test event)."""
    calls = []

    def fake_select(table, params):
        calls.append(table)
        if table == "evidence_events":
            return []
        if table == "mastery_state":
            return []
        raise AssertionError(f"unexpected select on {table}")

    monkeypatch.setattr(reconcile_mastery.db, "select", fake_select)

    reconcile_mastery.run(institution_id="inst-demo")

    assert "institutions" not in calls
