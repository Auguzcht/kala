"""UPDATED for the fifth worker job (ingestWalk). The tests that enumerated
exactly four jobs now enumerate five, in the handler's run order (reconcile,
ingest walk, embed, tag, readiness). ingestWalk sits before embedBackfill:
embedding reads chunks the walk may have just stored, same reasoning that
already places embed before tag. Everything else is unchanged from the
repo's existing test_handler.py — diff this against your copy before
dropping it in, so you can see it is only the job-list additions.
"""
from app import handler as handler_module
from app.handler import handler
from app.jobs import embed_backfill, ingest_walk, readiness_snapshot, reconcile_mastery, tag_backfill


def test_handler_runs_all_jobs_and_threads_scope(monkeypatch) -> None:
    calls = []

    def make_fake(name):
        def fake_run(*, institution_id=None):
            calls.append((name, institution_id))
            return {"ran": name}
        return fake_run

    monkeypatch.setattr(reconcile_mastery, "run", make_fake("reconcileMastery"))
    monkeypatch.setattr(ingest_walk, "run", make_fake("ingestWalk"))
    monkeypatch.setattr(embed_backfill, "run", make_fake("embedBackfill"))
    monkeypatch.setattr(tag_backfill, "run", make_fake("tagBackfill"))
    monkeypatch.setattr(readiness_snapshot, "run", make_fake("readinessSnapshot"))

    result = handler({"scope": {"institution_id": "inst-1"}}, None)

    assert result["ok"] is True
    assert result["errors"] == {}
    assert result["results"] == {
        "reconcileMastery": {"ran": "reconcileMastery"},
        "ingestWalk": {"ran": "ingestWalk"},
        "embedBackfill": {"ran": "embedBackfill"},
        "tagBackfill": {"ran": "tagBackfill"},
        "readinessSnapshot": {"ran": "readinessSnapshot"},
    }
    # Every job gets the same institution_id parsed from event["scope"], in
    # the handler's declared order (ingest walk before embed: embed reads
    # chunks the walk may have just stored; embed before tag: tag reads
    # chunks embed may have just backfilled).
    assert calls == [
        ("reconcileMastery", "inst-1"),
        ("ingestWalk", "inst-1"),
        ("embedBackfill", "inst-1"),
        ("tagBackfill", "inst-1"),
        ("readinessSnapshot", "inst-1"),
    ]


def test_handler_with_no_event_scopes_to_every_institution(monkeypatch) -> None:
    seen_institution_ids = []

    def fake_run(*, institution_id=None):
        seen_institution_ids.append(institution_id)
        return {}

    monkeypatch.setattr(reconcile_mastery, "run", fake_run)
    monkeypatch.setattr(ingest_walk, "run", fake_run)
    monkeypatch.setattr(embed_backfill, "run", fake_run)
    monkeypatch.setattr(tag_backfill, "run", fake_run)
    monkeypatch.setattr(readiness_snapshot, "run", fake_run)

    handler(None, None)  # Lambda can invoke with event=None on a schedule

    assert seen_institution_ids == [None, None, None, None, None]


def test_handler_isolates_a_raising_job_from_the_others(monkeypatch) -> None:
    """The core failure-isolation guarantee: one job raising must not stop
    the others from running, and must not raise out of handler() itself."""

    def raising_run(*, institution_id=None):
        raise RuntimeError("boom")

    def fake_ok_run(*, institution_id=None):
        return {"ok": True}

    monkeypatch.setattr(reconcile_mastery, "run", raising_run)
    monkeypatch.setattr(ingest_walk, "run", fake_ok_run)
    monkeypatch.setattr(embed_backfill, "run", fake_ok_run)
    monkeypatch.setattr(tag_backfill, "run", fake_ok_run)
    monkeypatch.setattr(readiness_snapshot, "run", fake_ok_run)

    result = handler({}, None)

    assert result["ok"] is False
    assert result["errors"] == {"reconcileMastery": "boom"}
    # Every job after the raising one still ran and reported results.
    assert result["results"] == {
        "ingestWalk": {"ok": True},
        "embedBackfill": {"ok": True},
        "tagBackfill": {"ok": True},
        "readinessSnapshot": {"ok": True},
    }


def test_handler_logs_job_start_and_completion(monkeypatch, caplog) -> None:
    """Observability: each job logs a start line and a done/failed line with
    a duration, via the structured logger, not print()."""
    monkeypatch.setattr(reconcile_mastery, "run", lambda **kw: {"pairsChecked": 3})
    monkeypatch.setattr(ingest_walk, "run", lambda **kw: {"jobsAdvanced": 0})
    monkeypatch.setattr(embed_backfill, "run", lambda **kw: {"embedded": 1})
    monkeypatch.setattr(tag_backfill, "run", lambda **kw: {"tagged": 4})
    monkeypatch.setattr(readiness_snapshot, "run", lambda **kw: {"snapshots": 2})

    with caplog.at_level("INFO", logger="kala.worker"):
        handler({}, None)

    messages = [r.getMessage() for r in caplog.records]
    assert any("job start name=reconcileMastery" in m for m in messages)
    assert any("job done name=reconcileMastery" in m and "duration_ms=" in m for m in messages)
    assert any("job start name=ingestWalk" in m for m in messages)
    assert any("job start name=tagBackfill" in m for m in messages)
    assert handler_module.logger.name == "kala.worker"
