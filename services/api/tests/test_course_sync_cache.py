"""Tests for the course-resolution cache and launch-sync cooldown helpers.

These exist because Kala burned a 10,000-request Blackboard quota by re-asking
the LMS for things it already knew. The pure functions below are the pieces
that make the caching safe: they must FAIL OPEN (degrade to the pre-fix
behavior) rather than break a launch, because the migration that adds the
underlying columns may not be applied yet.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.db import supabase as db


# ---- course lookup by LMS external id (Fix 1) ----------------------------


def test_lookup_returns_the_row_when_present(monkeypatch) -> None:
    monkeypatch.setattr(
        db, "select",
        lambda table, params: [{"id": "c1", "lms_course_id": "ref-ME301"}],
    )
    found = db.course_by_lms_external_id(institution_id="inst-1", lms_course_external_id="ME301")
    assert found["lms_course_id"] == "ref-ME301"


def test_lookup_returns_none_when_absent(monkeypatch) -> None:
    monkeypatch.setattr(db, "select", lambda table, params: [])
    assert db.course_by_lms_external_id(
        institution_id="inst-1", lms_course_external_id="ME301",
    ) is None


def test_lookup_fails_open_when_the_column_is_not_migrated(monkeypatch) -> None:
    """THE important one. Migration 0016 adds lms_course_external_id; until the
    user applies it, PostgREST answers a select naming that column with 400.
    That must degrade to "not found" (resolve over REST, the pre-fix path) and
    never to a raised exception, or a missing migration becomes an outage."""
    def unmigrated(table, params):
        raise RuntimeError("column courses.lms_course_external_id does not exist")

    monkeypatch.setattr(db, "select", unmigrated)
    assert db.course_by_lms_external_id(
        institution_id="inst-1", lms_course_external_id="ME301",
    ) is None


def test_lookup_fails_open_on_a_transient_read_error(monkeypatch) -> None:
    monkeypatch.setattr(db, "select", lambda table, params: (_ for _ in ()).throw(OSError("net")))
    assert db.course_by_lms_external_id(
        institution_id="inst-1", lms_course_external_id="ME301",
    ) is None


def test_get_or_create_course_omits_the_external_id_when_not_resolved(monkeypatch) -> None:
    """A caller that found the course locally has nothing new to record. The
    key must be OMITTED rather than sent as null, so a plain upsert cannot
    blank out an id an earlier launch already resolved."""
    captured: list[dict] = []
    monkeypatch.setattr(
        db, "upsert",
        lambda table, rows, on_conflict: captured.extend(rows) or [{"id": "c1"}],
    )
    db.get_or_create_course(institution_id="i", lms_course_id="ref", title="T")
    assert "lms_course_external_id" not in captured[0]


def test_get_or_create_course_persists_the_external_id_when_resolved(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(
        db, "upsert",
        lambda table, rows, on_conflict: captured.extend(rows) or [{"id": "c1"}],
    )
    db.get_or_create_course(
        institution_id="i", lms_course_id="ref", title="T", lms_course_external_id="ME301",
    )
    assert captured[0]["lms_course_external_id"] == "ME301"


# ---- cooldown window (Fix 2) ---------------------------------------------


def _course(**kw) -> dict:
    return {"id": "c1", **kw}


def test_never_synced_is_never_within_cooldown() -> None:
    """A null timestamp means the work has never run, so it must run now. This
    is what makes the first launch after the migration behave exactly as
    before — no accidental skipping of a course that has never been synced."""
    assert not db.course_synced_within(
        course=_course(last_roster_sync_at=None), column="last_roster_sync_at",
        cooldown_seconds=600,
    )


def test_absent_column_is_never_within_cooldown() -> None:
    """Same fail-open direction as the lookup: an unmigrated column is absent
    from the row, which must read as "sync now", not as an error."""
    assert not db.course_synced_within(
        course=_course(), column="last_skill_seed_at", cooldown_seconds=600,
    )


def test_a_recent_stamp_is_within_cooldown() -> None:
    recent = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    assert db.course_synced_within(
        course=_course(last_roster_sync_at=recent), column="last_roster_sync_at",
        cooldown_seconds=600,
    )


def test_an_old_stamp_is_outside_cooldown() -> None:
    """The self-healing contract: past the window, the work runs again."""
    old = (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat()
    assert not db.course_synced_within(
        course=_course(last_roster_sync_at=old), column="last_roster_sync_at",
        cooldown_seconds=600,
    )


def test_postgres_z_suffix_timestamps_parse() -> None:
    """PostgREST returns `...+00:00`, but a client or a future column could
    return the `Z` form; both must land on the same instant rather than
    silently failing open forever."""
    recent = (datetime.now(timezone.utc) - timedelta(seconds=30)).replace(
        tzinfo=None,
    ).isoformat() + "Z"
    assert db.course_synced_within(
        course=_course(last_roster_sync_at=recent), column="last_roster_sync_at",
        cooldown_seconds=600,
    )


def test_an_unparseable_stamp_fails_open_to_syncing() -> None:
    """Garbage in the column must not suppress the work indefinitely."""
    assert not db.course_synced_within(
        course=_course(last_roster_sync_at="not a timestamp"),
        column="last_roster_sync_at", cooldown_seconds=600,
    )


def test_unknown_column_is_rejected_on_read_and_write() -> None:
    """The column name reaches PostgREST as a payload KEY. The allow-list is
    what keeps that from being a write primitive if a third caller appears."""
    with pytest.raises(ValueError):
        db.course_synced_within(
            course=_course(), column="title; drop table courses", cooldown_seconds=600,
        )
    with pytest.raises(ValueError):
        db.touch_course_sync_timestamp(course_id="c1", column="institution_id")


def test_stamping_writes_an_iso_timestamp(monkeypatch) -> None:
    captured: list[tuple] = []
    monkeypatch.setattr(
        db, "update",
        lambda table, match, values: captured.append((table, match, values)),
    )
    db.touch_course_sync_timestamp(course_id="c1", column="last_roster_sync_at")

    values = captured[0][2]
    assert "last_roster_sync_at" in values
    # Round-trips as a real timestamp, so the cooldown read can parse it.
    parsed = datetime.fromisoformat(values["last_roster_sync_at"])
    assert parsed.tzinfo is not None


def test_stamping_failure_is_swallowed(monkeypatch) -> None:
    """Bookkeeping for a cooldown must never surface as a failed sync — the
    sync itself already succeeded."""
    monkeypatch.setattr(
        db, "update",
        lambda table, match, values: (_ for _ in ()).throw(RuntimeError("unmigrated column")),
    )
    db.touch_course_sync_timestamp(course_id="c1", column="last_skill_seed_at")
