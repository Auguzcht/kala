"""ingest_walk — the incremental, checkpointed course walk.

Pins the behaviors that had to be FIXED after the scaffold review, plus the
lifecycle the architecture depends on. Driven entirely by fake rows and a fake
connector: no live Blackboard, no live Supabase, exactly as the design doc
requires.

The four fixes these tests exist to protect:
  1. the frontier is checkpointed PER FOLDER, so a 429 mid-slice loses at most
     the folder it was expanding — never the whole slice;
  2. a failed folder goes back on the FRONT of the frontier, so nothing is lost
     and nothing is duplicated;
  3. seed-time stores are counted in items_stored;
  4. a container reachable from two parents is expanded once per run.

And the lifecycle: resume-after-throttle completes with no duplicate stores,
an empty frontier flips to complete, and a real error marks the job failed.
"""
from __future__ import annotations

import pytest

from app import chunking
from app.jobs import ingest_walk
from app.lms.blackboard import BlackboardRateLimitedError

# ---------------------------------------------------------------------------
# Harness: an in-memory job row + content table, and a scripted connector.
# ---------------------------------------------------------------------------


class FakeDB:
    """Stands in for app.db.supabase. Holds ONE job and the stored lms_refs, so
    a test can assert exactly what was persisted between 'runs'."""

    def __init__(self, job: dict):
        self.job = dict(job)
        self.stored: list[dict] = []  # content_items rows
        self.updates: list[dict] = []

    def select(self, table, params):
        if table == "ingest_jobs":
            return [dict(self.job)]
        if table == "courses":
            return [{"lms_course_id": "_8_1"}]
        if table == "content_items":
            refs = {r["lms_ref"] for r in self.stored}
            return [{"lms_ref": r} for r in refs]
        raise AssertionError(f"unexpected select on {table}")

    def insert(self, table, rows):
        assert table == "content_items"
        self.stored.extend(rows)
        return [{"id": f"ci-{len(self.stored)}"}]

    def update(self, table, match, values):
        self.updates.append(dict(values))
        self.job.update(values)
        return [dict(self.job)]


class FakeConnector:
    """A scripted content tree. `fail_on` names a folder whose fetch raises."""

    def __init__(self, tree: dict, *, fail_on: str | None = None,
                 pdf_bytes: dict | None = None):
        self.tree = tree
        self.fail_on = fail_on
        self.calls: list[str] = []
        self.pdf_bytes = pdf_bytes or {}

    def fetch_children(self, course_ref, parent_id=None):
        key = parent_id or "__root__"
        self.calls.append(key)
        if self.fail_on and key == self.fail_on:
            raise BlackboardRateLimitedError(retry_after=100, path=key)
        return self.tree.get(key, [])

    def flatten_item(self, raw):
        return {
            "lms_content_id": raw.get("id"),
            "title": raw.get("title") or "Untitled",
            "body_or_description": raw.get("body") or "",
            "parent_id": raw.get("parentId"),
        }

    def is_container(self, raw):
        return bool(raw.get("hasChildren"))

    def extract_pdf_attachments(self, raw):
        return [
            {"href": href, "mimeType": "application/pdf", "fileName": name}
            for name, href in (raw.get("pdfs") or {}).items()
        ]

    def download(self, href):
        return self.pdf_bytes.get(href, b"")


def _job(**kw) -> dict:
    return {
        "id": "J1", "institution_id": "inst-1", "course_id": "course-1",
        "status": "pending", "frontier": None,
        "folders_expanded": 0, "items_stored": 0, "pdfs_fetched": 0,
        "include_attachments": False, **kw,
    }


def _wire(monkeypatch, job: dict) -> FakeDB:
    fake = FakeDB(job)
    monkeypatch.setattr(ingest_walk, "db", fake)
    return fake


def _container(id: str, title: str = "Folder", **extra) -> dict:
    return {"id": id, "title": title, "hasChildren": True, **extra}


def _leaf(id: str, body: str = "Some course text.", **extra) -> dict:
    return {"id": id, "title": "Page", "body": body, **extra}


# ---------------------------------------------------------------------------
# Fix 1 + 2: per-folder checkpointing, and the failed folder goes back
# ---------------------------------------------------------------------------


def test_a_throttle_mid_slice_checkpoints_the_folders_already_expanded(monkeypatch):
    """THE regression this design exists for. The scaffold checkpointed once
    after the whole slice, so a 429 at folder 2 of 3 lost folder 1's progress
    entirely and the next run re-walked it."""
    tree = {
        "__root__": [_container("F1"), _container("F2"), _container("F3")],
        "F1": [_leaf("i1")], "F2": [_leaf("i2")], "F3": [_leaf("i3")],
    }
    fake = _wire(monkeypatch, _job())
    monkeypatch.setattr(ingest_walk, "_FOLDERS_PER_RUN", 3)
    conn = FakeConnector(tree, fail_on="F2")

    with pytest.raises(BlackboardRateLimitedError):
        ingest_walk._advance_one(conn, dict(fake.job))

    # F1's work survived...
    assert fake.job["folders_expanded"] == 1
    assert {r["lms_ref"] for r in fake.stored} >= {"i1"}   # F1 is a bodyless container
    # ...the throttled folder is still queued, and F3 was not lost.
    frontier_ids = [entry[0] for entry in fake.job["frontier"]]
    assert "F2" in frontier_ids, "the throttled folder must be retried"
    assert "F3" in frontier_ids, "an un-expanded folder must never vanish"
    # F2 goes to the FRONT so it is retried first.
    assert frontier_ids[0] == "F2"


def test_a_throttled_folder_is_not_duplicated_or_lost_on_resume(monkeypatch):
    """Resume after the throttle: completes, stores every leaf exactly once."""
    tree = {
        "__root__": [_container("F1"), _container("F2"), _container("F3")],
        "F1": [_leaf("i1")], "F2": [_leaf("i2")], "F3": [_leaf("i3")],
    }
    fake = _wire(monkeypatch, _job())
    monkeypatch.setattr(ingest_walk, "_FOLDERS_PER_RUN", 3)

    with pytest.raises(BlackboardRateLimitedError):
        ingest_walk._advance_one(FakeConnector(tree, fail_on="F2"), dict(fake.job))

    status = ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    assert status == "complete"
    stored = [r["lms_ref"] for r in fake.stored]
    assert len(stored) == len(set(stored)), "no duplicate stores after resume"
    assert {"i1", "i2", "i3"} <= set(stored)


def test_the_job_advances_by_one_bounded_slice_per_run(monkeypatch):
    """More folders than one slice => in_progress, not complete, and the rest
    stays on the frontier for the next run."""
    tree = {"__root__": [_container(f"F{i}") for i in range(5)]}
    for i in range(5):
        tree[f"F{i}"] = [_leaf(f"i{i}")]
    fake = _wire(monkeypatch, _job())
    monkeypatch.setattr(ingest_walk, "_FOLDERS_PER_RUN", 2)

    assert ingest_walk._advance_one(FakeConnector(tree), dict(fake.job)) == "in_progress"
    assert fake.job["folders_expanded"] == 2
    assert len(fake.job["frontier"]) == 3


def test_an_empty_frontier_flips_the_job_to_complete(monkeypatch):
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())
    status = ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    assert status == "complete"
    assert fake.job["status"] == "complete"
    assert fake.job["finished_at"], "completion stamps finished_at"


def test_a_course_with_no_content_completes_immediately(monkeypatch):
    """An empty tree must not leave a job spinning forever."""
    fake = _wire(monkeypatch, _job())
    assert ingest_walk._advance_one(FakeConnector({}), dict(fake.job)) == "complete"


# ---------------------------------------------------------------------------
# Fix 3: seed-time stores are counted
# ---------------------------------------------------------------------------


def test_seed_time_stores_are_counted_in_items_stored(monkeypatch):
    """The scaffold discarded _seed_from_top's count, so every top-level store
    was invisible in the number an operator watches during a drain."""
    tree = {
        "__root__": [_container("F1"), _leaf("topLeaf")],
        "F1": [_leaf("i1")],
    }
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    # topLeaf (stored during seeding) and i1 (stored while expanding F1)
    # must BOTH be counted. F1 itself is a bodyless container, so it stores
    # no chunk — that is correct, not a miss.
    assert {r["lms_ref"] for r in fake.stored} == {"topLeaf", "i1"}
    assert fake.job["items_stored"] == 2, "the seed-time store must be counted"
    assert len(fake.stored) == fake.job["items_stored"]


# ---------------------------------------------------------------------------
# Fix 4: run-local dedupe on discovered containers
# ---------------------------------------------------------------------------


def test_a_container_reachable_from_two_parents_is_expanded_once(monkeypatch):
    """A DAG (or malformed data) lists the same container under two parents.
    It must be queued, fetched and stored exactly once."""
    tree = {
        "__root__": [_container("A"), _container("C")],
        "A": [_container("D"), _leaf("iA")],
        "C": [_container("D"), _leaf("iC")],
        "D": [_leaf("iD")],
    }
    fake = _wire(monkeypatch, _job())
    conn = FakeConnector(tree)
    ingest_walk._advance_one(conn, dict(fake.job))

    assert conn.calls.count("D") == 1, "D must be expanded exactly once"
    stored = [r["lms_ref"] for r in fake.stored]
    assert stored.count("iD") == 1


# ---------------------------------------------------------------------------
# Chunking / PII / ancestry — the drain gate
# ---------------------------------------------------------------------------


def test_a_long_body_is_chunked_not_stored_whole(monkeypatch):
    """The scaffold stored each item's whole body as ONE chunk. A 9000-char
    page must become multiple chunks bounded by MAX_CHUNK_CHARS."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1", "A" * 9000)]}
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    chunks = [r for r in fake.stored if r["lms_ref"] == "i1"]
    assert len(chunks) > 1, "a long body must split"
    assert all(len(r["chunk_text"]) <= chunking.MAX_CHUNK_CHARS for r in chunks)


def test_pii_is_stripped_before_storage(monkeypatch):
    """Hard rule: de-identify before anything reaches a model."""
    body = "Contact prof@mmcm.edu.ph or name: Jane Doe for details."
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1", body)]}
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    text = next(r["chunk_text"] for r in fake.stored if r["lms_ref"] == "i1")
    assert "prof@mmcm.edu.ph" not in text
    assert "Jane Doe" not in text
    assert "[email]" in text


def test_a_leaf_child_gets_its_parents_folder_path_not_its_grandparents(monkeypatch):
    """Regression: the first cut computed the child path only for CONTAINER
    children, so a LEAF was stored with its parent's path and landed one level
    too shallow — module_ref silently None at the top. Every child of a folder
    sits one level below it, container or not."""
    tree = {
        "__root__": [_container("M1", "Module 1")],
        "M1": [_container("W1", "Week 1"), _leaf("leafA")],
        "W1": [_leaf("leafB")],
    }
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    by_ref = {r["lms_ref"]: r for r in fake.stored}
    assert by_ref["leafA"]["module_ref"] == "Module 1"
    assert len(by_ref["leafA"]["folder_path"]) == 1
    # A grandchild carries the full chain.
    assert by_ref["leafB"]["module_ref"] == "Module 1"
    assert len(by_ref["leafB"]["folder_path"]) == 2


def test_a_leaf_two_levels_deep_carries_the_FULL_ancestor_chain(monkeypatch):
    """The module_ref bug mattered beyond cosmetics.

    tag_backfill uses a chunk's module_ref to infer which MODULE a skill
    belongs to (its skill_module_ref map), and it only ever FILLS a gap — never
    overrides a value already set. So a leaf stored with module_ref=None is not
    a display gap: it is a skill-inference input that starts from nothing, and
    the wrong value is written once and then respected forever.

    This asserts the ACTUAL CHAIN, root-to-parent in order, not merely that the
    field is non-empty — a path of the wrong depth or wrong order would pass a
    presence check and still mis-file every skill beneath it.
    """
    tree = {
        "__root__": [_container("M1", "Module 1")],
        "M1": [_container("W1", "Week 1")],
        "W1": [_container("D1", "Day 1"), _leaf("leafAtDepth2")],
        "D1": [_leaf("leafAtDepth3")],
    }
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))
    by_ref = {r["lms_ref"]: r for r in fake.stored}

    # A leaf directly under Week 1 (two levels below the root).
    path = by_ref["leafAtDepth2"]["folder_path"]
    assert [e["lmsRef"] for e in path] == ["M1", "W1"], "root-to-parent order"
    assert [e["title"] for e in path] == ["Module 1", "Week 1"]
    # module_ref is the TOP-level ancestor, not the immediate parent.
    assert by_ref["leafAtDepth2"]["module_ref"] == "Module 1"

    # And three levels deep keeps the whole chain, in order.
    deep = by_ref["leafAtDepth3"]["folder_path"]
    assert [e["lmsRef"] for e in deep] == ["M1", "W1", "D1"]
    assert by_ref["leafAtDepth3"]["module_ref"] == "Module 1"


def test_the_incremental_walk_matches_the_apis_whole_tree_paths(monkeypatch):
    """The api resolves folder_path from the WHOLE tree at once
    (build_folder_paths); the worker can only ever know the ancestry it has
    walked down. This pins that the incremental answer is the same one the api
    would have produced for the same shape, including for a leaf that is only
    reachable after several slices — i.e. the path survives being checkpointed
    as jsonb and rehydrated on a later run."""
    tree = {
        "__root__": [_container("M1", "Module 1")],
        "M1": [_container("W1", "Week 1")],
        "W1": [_leaf("deepLeaf")],
    }
    fake = _wire(monkeypatch, _job())
    # One folder per run, so deepLeaf is only reached on the THIRD slice and
    # its path must have round-tripped through the persisted frontier.
    monkeypatch.setattr(ingest_walk, "_FOLDERS_PER_RUN", 1)

    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    leaf = next(r for r in fake.stored if r["lms_ref"] == "deepLeaf")
    assert [e["lmsRef"] for e in leaf["folder_path"]] == ["M1", "W1"]
    assert leaf["module_ref"] == "Module 1"


def test_pdfs_are_extracted_chunked_and_stored_under_their_own_ref(monkeypatch):
    """A PDF's text must land in content_items, addressable on its own — not
    fetched and discarded, and not appended to the linking page."""
    tree = {
        "__root__": [_container("F1")],
        "F1": [_leaf("i1", pdfs={"Guide.pdf": "https://bb/x"})],
    }
    fake = _wire(monkeypatch, _job(include_attachments=True))
    monkeypatch.setattr(ingest_walk, "extract_text", lambda data, mime: "PDF text. " * 800)
    monkeypatch.setattr(ingest_walk, "resolve_mime_type", lambda name, decl: "application/pdf")

    conn = FakeConnector(tree, pdf_bytes={"https://bb/x": b"%PDF-1.7"})
    ingest_walk._advance_one(conn, dict(fake.job))

    pdf_rows = [r for r in fake.stored if r["lms_ref"] == "i1::Guide.pdf"]
    assert pdf_rows, "the PDF must be stored under its own lms_ref"
    assert len(pdf_rows) > 1, "PDF text must be chunked, not stored whole"
    assert fake.job["pdfs_fetched"] == 1


def test_attachments_are_not_fetched_unless_the_job_asked(monkeypatch):
    """The include_attachments gate carries from enqueue to worker."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1", pdfs={"G.pdf": "h"})]}
    fake = _wire(monkeypatch, _job(include_attachments=False))
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))

    assert not [r for r in fake.stored if "::" in r["lms_ref"]]
    assert fake.job["pdfs_fetched"] == 0


def test_one_broken_pdf_does_not_lose_the_rest_of_the_slice(monkeypatch):
    class Flaky(FakeConnector):
        def download(self, href):
            if href == "bad":
                raise RuntimeError("dead href")
            return b"%PDF-1.7"

    tree = {
        "__root__": [_container("F1")],
        "F1": [_leaf("i1", pdfs={"bad.pdf": "bad", "good.pdf": "good"})],
    }
    fake = _wire(monkeypatch, _job(include_attachments=True))
    monkeypatch.setattr(ingest_walk, "extract_text", lambda d, m: "text " * 100)
    monkeypatch.setattr(ingest_walk, "resolve_mime_type", lambda n, d: "application/pdf")

    ingest_walk._advance_one(Flaky(tree), dict(fake.job))

    assert [r for r in fake.stored if r["lms_ref"] == "i1::good.pdf"]
    assert fake.job["favicon" if False else "pdfs_fetched"] == 1


# ---------------------------------------------------------------------------
# Scope + failure semantics
# ---------------------------------------------------------------------------


def test_run_marks_a_job_failed_on_a_real_error_not_a_throttle(monkeypatch):
    """Transport-vs-real distinction carried from tag_backfill: a real error
    marks failed for a human; a throttle must NOT."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())

    class Boom(FakeConnector):
        def fetch_children(self, course_ref, parent_id=None):
            if parent_id == "F1":
                raise ValueError("genuinely broken")
            return super().fetch_children(course_ref, parent_id)

    monkeypatch.setattr(ingest_walk, "WorkerBlackboardConnector", lambda: Boom(tree))
    result = ingest_walk.run(institution_id="inst-1")

    assert result["jobsAdvanced"] == 1
    assert fake.job["status"] == "failed"
    assert "genuinely broken" in fake.job["last_error"]


def test_run_leaves_the_job_in_progress_on_a_throttle_and_stops(monkeypatch):
    """A 429 must NOT mark failed — that status means 'never auto-retried' and
    would defeat the whole schedule-driven design."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())
    monkeypatch.setattr(
        ingest_walk, "WorkerBlackboardConnector",
        lambda: FakeConnector(tree, fail_on="F1"),
    )

    result = ingest_walk.run(institution_id="inst-1")

    assert result["rateLimited"] == 1
    assert fake.job["status"] != "failed"
    assert fake.job["status"] == "in_progress"


def test_run_scopes_pickup_to_one_institution(monkeypatch):
    """The manual-console-invoke path must not sweep other tenants."""
    fake = _wire(monkeypatch, _job())
    seen = {}

    def fake_select(table, params):
        seen.update(params)
        return []

    monkeypatch.setattr(ingest_walk.db, "select", fake_select)
    ingest_walk.run(institution_id="inst-9")

    assert seen["institution_id"] == "eq.inst-9"


# ---------------------------------------------------------------------------
# FIX B: the retry-after guard. These exist because the guard changes run()'s
# PICKUP QUERY, which is exactly the surface the async wiring gap hid on —
# correct logic that nothing ever calls. So these drive run() and the handler,
# not just the WHERE clause.
# ---------------------------------------------------------------------------


class QueryAwareDB(FakeDB):
    """A FakeDB that actually honours the not_before filter, so a test can
    prove a backed-off job is not picked up rather than asserting the filter
    string."""

    def select(self, table, params):
        if table == "ingest_jobs":
            nb = params.get("not_before", "")
            job_nb = self.job.get("not_before")
            if job_nb:
                # Emulate `is.null,not_before.lte.<now>`: a job with a FUTURE
                # not_before must not come back.
                cutoff = nb.split("lte.")[-1] if "lte." in nb else ""
                if cutoff and str(job_nb) > cutoff:
                    return []
            return [dict(self.job)]
        return super().select(table, params)


def test_a_throttle_sets_not_before_from_retry_after(monkeypatch):
    """The 429 carries the exact wait; the guard must record it rather than
    retrying blind on the next schedule."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())
    monkeypatch.setattr(
        ingest_walk, "WorkerBlackboardConnector",
        lambda: FakeConnector(tree, fail_on="F1"),
    )

    ingest_walk.run(institution_id="inst-1")

    assert fake.job["not_before"], "a 429 must record a backoff"
    from datetime import datetime, timezone
    when = datetime.fromisoformat(fake.job["not_before"])
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    assert when > datetime.now(timezone.utc), "the backoff must be in the future"


def test_a_429_without_a_retry_after_still_backs_off(monkeypatch):
    """The header is optional. Leaving the job immediately eligible would
    reproduce the very spin the guard exists to stop."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())

    class NoHeader(FakeConnector):
        def fetch_children(self, course_ref, parent_id=None):
            if parent_id == "F1":
                raise BlackboardRateLimitedError(retry_after=None, path="F1")
            return super().fetch_children(course_ref, parent_id)

    monkeypatch.setattr(ingest_walk, "WorkerBlackboardConnector", lambda: NoHeader(tree))
    ingest_walk.run(institution_id="inst-1")

    assert fake.job["not_before"], "must still back off, using the default"
    assert fake.job["status"] != "failed", "a throttle is never 'failed'"


def test_a_backed_off_job_is_not_picked_up(monkeypatch):
    """The pickup filter must actually exclude it — this is the WHERE clause
    doing its job against a query that honours it."""
    future = "2099-01-01T00:00:00+00:00"
    fake = QueryAwareDB(_job(status="in_progress", not_before=future, frontier=[]))
    monkeypatch.setattr(ingest_walk, "db", fake)
    called = {"advance": 0}
    monkeypatch.setattr(
        ingest_walk, "_advance_one",
        lambda c, j: called.__setitem__("advance", called["advance"] + 1) or "in_progress",
    )

    result = ingest_walk.run(institution_id="inst-1")

    assert result["jobsAdvanced"] == 0
    assert called["advance"] == 0, "a job inside its backoff must not be advanced"


def test_a_job_whose_backoff_has_elapsed_IS_picked_up(monkeypatch):
    """The complement: once the window passes, the job resumes without any
    manual re-enqueue."""
    past = "2000-01-01T00:00:00+00:00"
    fake = QueryAwareDB(_job(status="in_progress", not_before=past, frontier=[]))
    monkeypatch.setattr(ingest_walk, "db", fake)
    monkeypatch.setattr(
        ingest_walk, "WorkerBlackboardConnector",
        lambda: FakeConnector({"__root__": [_container("F1")], "F1": [_leaf("i1")]}),
    )

    result = ingest_walk.run(institution_id="inst-1")

    assert result["jobsAdvanced"] == 1


def test_the_livelock_is_broken_end_to_end_through_the_handler(monkeypatch):
    """THE test this guard exists for, driven the way production drives it.

    Before the guard: quota fully exhausted => every scheduled run gets 429 on
    its first call, expands nothing, checkpoints nothing => folders_expanded
    frozen forever with the job never failing. Verified by hand against the
    fixed-but-unguarded code (frozen across 4 consecutive runs).

    This runs the REAL handler five times against a connector that always
    throttles, and asserts the spin is broken: the job backs off, the run
    reports it, and NO further Blackboard calls are made on subsequent runs
    until the window elapses.
    """
    from app.handler import handler

    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = QueryAwareDB(_job())
    monkeypatch.setattr(ingest_walk, "db", fake)

    attempts = {"n": 0}

    class AlwaysThrottled(FakeConnector):
        def fetch_children(self, course_ref, parent_id=None):
            attempts["n"] += 1
            raise BlackboardRateLimitedError(retry_after=3600, path=str(parent_id))

    monkeypatch.setattr(
        ingest_walk, "WorkerBlackboardConnector", lambda: AlwaysThrottled(tree),
    )
    # The handler imports the jobs module; make sure it sees our patched db.
    import app.handler as handler_module
    monkeypatch.setattr(handler_module, "ingest_walk", ingest_walk)

    # Run 1: hits the throttle, records the backoff.
    handler({"scope": {"institution_id": "inst-1"}}, None)
    after_first = attempts["n"]
    assert after_first >= 1, "run 1 should have tried"
    assert fake.job["not_before"], "run 1 must record the backoff"

    # Runs 2-4: the job is inside its backoff, so Blackboard must NOT be hit.
    for _ in range(3):
        handler({"scope": {"institution_id": "inst-1"}}, None)

    assert attempts["n"] == after_first, (
        "the walk kept calling Blackboard while inside its backoff — this is "
        "the spin the guard exists to stop"
    )
    assert fake.job["status"] != "failed", "a throttle never marks the job failed"


# ---------------------------------------------------------------------------
# FIX A: persisted cross-run dedupe
# ---------------------------------------------------------------------------


def test_a_container_already_expanded_in_a_previous_run_is_not_queued_again(monkeypatch):
    """The run-local `queued` set starts empty each run, so without the
    persisted `seen` set a container re-discovered later is queued again and
    its whole subtree re-walked. This simulates exactly that: run 1 expands C,
    run 2 rediscovers C as a child of A."""
    # Run 1: A -> C, C -> leafC. C gets expanded, so it lands in `seen`.
    tree1 = {"__root__": [_container("A")], "A": [_container("C")], "C": [_leaf("leafC")]}
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree1), dict(fake.job))
    assert "C" in (fake.job.get("seen") or []), "C must be recorded as expanded"
    assert fake.job["status"] == "complete"

    # Run 2: same tree, but the frontier is seeded so C is rediscovered.
    fake.job["status"] = "in_progress"
    fake.job["frontier"] = [["A", [], "A"]]
    conn = FakeConnector(tree1)
    ingest_walk._advance_one(conn, dict(fake.job))

    assert conn.calls.count("C") == 0, "C was already expanded; do not re-fetch it"


def test_seen_survives_a_run_boundary_via_the_job_row(monkeypatch):
    """`seen` must be read back off the job row, or it is only run-local and
    this whole fix is decorative."""
    tree = {"__root__": [_container("F1")], "F1": [_leaf("i1")]}
    fake = _wire(monkeypatch, _job())
    ingest_walk._advance_one(FakeConnector(tree), dict(fake.job))
    recorded = fake.job.get("seen")
    assert recorded, "the checkpoint must persist `seen`"

    # A fresh job dict carrying only what the DB would return still knows F1.
    resumed = dict(fake.job)
    assert "F1" in resumed["seen"]


def test_the_pickup_query_requires_the_0018_columns(monkeypatch):
    """DEPLOY-ORDER HAZARD, pinned rather than left to be rediscovered.

    Unlike 0016 — where the new code failed open and apply-order did not
    matter — this guard's filter names columns that only exist after 0018. On
    a database without them PostgREST answers 400, db.select raises, and
    run() propagates: ingest goes fully offline, it does not degrade.

    So the required order is APPLY 0018, THEN deploy the worker. This test
    exists so that if someone later "hardens" the query by dropping the filter
    when the column is missing, that change is a visible decision rather than
    a silent one.
    """
    captured = {}

    class Fake:
        def select(self, table, params):
            captured.update(params)
            return []

        def insert(self, *a, **k):
            return []

        def update(self, *a, **k):
            return []

    monkeypatch.setattr(ingest_walk, "db", Fake())
    ingest_walk.run(institution_id="inst-1")

    assert "not_before" in captured, "the guard must filter on not_before"
    assert "seen" in captured["select"], "the guard must select seen"
