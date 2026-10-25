"""WI-25 query/cursor proof; route authorization is tested separately after SEC."""
from datetime import datetime
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.twin import evidence_history as history

INST, CALLER, USER, COURSE = [str(UUID(int=i)) for i in range(1, 5)]
SCOPE = dict(institution_id=INST, caller_id=CALLER, user_id=USER, course_id=COURSE)


def fixtures(monkeypatch, count=61):
    rows = [{"id": str(UUID(int=1000+i)), "created_at": f"2026-10-{25-i//20:02d}T12:00:00+00:00",
             "skill_id": None, "type": "practice", "correct": True} for i in range(count)]
    rows.sort(key=lambda e: (e["created_at"], e["id"]), reverse=True)
    calls = []
    def select(table, params):
        calls.append((table, params))
        assert table == "evidence_events"
        assert params["institution_id"] == f"eq.{INST}"
        assert params["user_id"] == f"eq.{USER}"
        assert params["course_id"] == f"eq.{COURSE}"
        assert params["order"] == "created_at.desc,id.desc"
        selected = rows
        if "or" in params:
            expr = params["or"]
            cutoff = expr.split("created_at.lt.")[1].split(",and(")[0]
            event_id = expr.split("id.lt.")[1].split(")")[0]
            selected = [e for e in rows if (datetime.fromisoformat(e["created_at"]), e["id"]) <
                        (datetime.fromisoformat(cutoff), event_id)]
        return selected[:int(params["limit"]) ]
    monkeypatch.setattr(history.db, "select", select)
    return rows, calls


def test_wi25_first_next_last_equal_timestamps(monkeypatch):
    rows, calls = fixtures(monkeypatch)
    first = history.history_page(**SCOPE)
    second = history.history_page(**SCOPE, cursor=first["nextCursor"])
    last = history.history_page(**SCOPE, cursor=second["nextCursor"])
    assert [len(p["evidence"]) for p in (first, second, last)] == [25, 25, 11]
    assert last["nextCursor"] is None
    assert [e["id"] for p in (first, second, last) for e in p["evidence"]] == [e["id"] for e in rows]
    assert len(calls) == 3


@pytest.mark.parametrize("count", [0, 1, 25])
def test_wi25_empty_exact_and_single(monkeypatch, count):
    fixtures(monkeypatch, count)
    page = history.history_page(**SCOPE)
    assert len(page["evidence"]) == count
    assert page["nextCursor"] is None


@pytest.mark.parametrize("cursor", ["", "not-a-cursor", "a.b", "x"*2049, "a.b.c"])
def test_wi25_invalid_cursor_no_query(monkeypatch, cursor):
    _, calls = fixtures(monkeypatch)
    with pytest.raises(HTTPException) as error:
        history.history_page(**SCOPE, cursor=cursor)
    assert error.value.status_code == 422
    assert not calls


def test_wi25_tamper_and_scope_mismatch(monkeypatch):
    _, calls = fixtures(monkeypatch)
    cursor = history.history_page(**SCOPE, limit=1)["nextCursor"]
    for key in SCOPE:
        changed = {**SCOPE, key: str(UUID(int=99))}
        with pytest.raises(HTTPException) as error:
            history.history_page(**changed, cursor=cursor)
        assert error.value.status_code == 422
    changed_cursor = ("A" if cursor[0] != "A" else "B") + cursor[1:]
    with pytest.raises(HTTPException) as error:
        history.history_page(**SCOPE, cursor=changed_cursor)
    assert error.value.status_code == 422
    assert len(calls) == 1


@pytest.mark.parametrize("limit", [0, -1, 101, True])
def test_wi25_limit_bounds(monkeypatch, limit):
    _, calls = fixtures(monkeypatch)
    with pytest.raises(HTTPException) as error:
        history.history_page(**SCOPE, limit=limit)
    assert error.value.status_code == 422
    assert not calls


@pytest.mark.parametrize("limit", [1, 100])
def test_wi25_valid_limit(monkeypatch, limit):
    fixtures(monkeypatch)
    assert len(history.history_page(**SCOPE, limit=limit)["evidence"]) == min(limit, 61)


def test_wi25_concurrent_arrival_and_missing_anchor(monkeypatch):
    rows, _ = fixtures(monkeypatch)
    first = history.history_page(**SCOPE)
    anchor = first["evidence"][-1]["id"]
    rows[:] = [e for e in rows if e["id"] != anchor]
    rows.insert(0, {**rows[0], "id": str(UUID(int=9999)), "created_at": "2026-10-26T00:00:00+00:00"})
    second = history.history_page(**SCOPE, cursor=first["nextCursor"])
    assert not {e["id"] for e in first["evidence"]} & {e["id"] for e in second["evidence"]}
    assert str(UUID(int=9999)) not in {e["id"] for e in second["evidence"]}


def test_wi25_cursor_rotation_and_noncanonical_encoding(monkeypatch):
    fixtures(monkeypatch)
    cursor = history.history_page(**SCOPE, limit=1)["nextCursor"]
    with pytest.raises(HTTPException):
        history.history_page(**SCOPE, cursor=cursor + "=")
    monkeypatch.setattr(history, "_key", lambda: b"synthetic rotated key")
    with pytest.raises(HTTPException) as error:
        history.history_page(**SCOPE, cursor=cursor)
    assert error.value.status_code == 422


@pytest.mark.parametrize("replacement", [{"v": 2}, {"v": True}, {"t": "bad"},
                                         {"t": "2026-10-25T12:00:00"}, {"id": "bad"}])
def test_wi25_signed_cursor_shape_validation(monkeypatch, replacement):
    import json
    import hmac
    fixtures(monkeypatch)
    scope = history._scope(**SCOPE)
    payload = {"v": 1, "s": scope, "t": "2026-10-25T12:00:00Z", "id": str(UUID(int=1000))}
    raw = json.dumps({**payload, **replacement}).encode()
    cursor = history._encode(raw) + "." + history._encode(hmac.digest(history._key(), raw, "sha256"))
    with pytest.raises(HTTPException) as error:
        history.history_page(**SCOPE, cursor=cursor)
    assert error.value.status_code == 422


def test_wi25_skill_names_are_scoped_and_approved(monkeypatch):
    skill_id = str(UUID(int=999))
    def select(table, params):
        assert params["institution_id"] == f"eq.{INST}"
        assert params["course_id"] == f"eq.{COURSE}"
        if table == "evidence_events":
            return [{"id": str(UUID(int=1000)), "created_at": "2026-10-25T12:00:00Z",
                     "skill_id": skill_id, "type": "practice", "correct": None}]
        assert params["id"] == f"in.({skill_id})"
        assert params["status"] == "eq.approved"
        return [{"id": skill_id, "name": "Synthetic approved skill"}]
    monkeypatch.setattr(history.db, "select", select)
    event = history.history_page(**SCOPE)["evidence"][0]
    assert event["skillName"] == "Synthetic approved skill"
    assert event["createdAt"] == "2026-10-25T12:00:00Z"
