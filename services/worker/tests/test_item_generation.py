from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.jobs import item_generation


class FakeDB:
    def __init__(self, rows, *, existing_ids=()):
        self.rows = [dict(row) for row in rows]
        self.existing_ids = set(existing_ids)
        self.updates = []
        self.inserted = []

    def select(self, table, params):
        if table == "item_generation_jobs":
            if params.get("status") == "eq.in_progress":
                cutoff = datetime.fromisoformat(params["started_at"].split("lt.", 1)[1])
                return [
                    r for r in self.rows
                    if r["status"] == "in_progress"
                    and datetime.fromisoformat(r["started_at"]) < cutoff
                ]
            return [r for r in self.rows if r["status"] == "pending"]
        if table == "generated_items":
            item_id = params["id"].split("eq.", 1)[1]
            return [{"id": item_id}] if item_id in self.existing_ids else []
        if table == "skills":
            return [{"id": "skill-1", "name": "Cloud concepts", "bloom_level": "understand"}]
        raise AssertionError(table)

    def update(self, table, filters, values):
        assert table == "item_generation_jobs"
        self.updates.append((filters, values))
        row_id = filters["id"].split("eq.", 1)[1]
        for row in self.rows:
            if row["id"] == row_id:
                row.update(values)
                return [dict(row)]
        return []


class LessonDB(FakeDB):
    def __init__(self, rows):
        super().__init__(rows)
        self.step = {
            "id": "step-1",
            "lesson_id": "lesson-1",
            "check_item_id": None,
        }

    def select(self, table, params):
        if table == "guided_lesson_steps":
            assert params["id"] == "eq.step-1"
            assert params["guided_lessons.institution_id"] == "eq.inst-1"
            assert "guided_lessons!inner(institution_id)" in params["select"]
            return [{**self.step, "guided_lessons": {"institution_id": "inst-1"}}]
        return super().select(table, params)

    def update(self, table, filters, values):
        if table == "guided_lesson_steps":
            assert filters == {"id": "eq.step-1", "lesson_id": "eq.lesson-1"}
            self.step.update(values)
            return [dict(self.step)]
        return super().update(table, filters, values)

    def insert(self, table, rows):
        self.inserted.extend(rows)
        return rows


def _row(job_id, *, offset=0, status="pending", attempt_count=0, started_at=None):
    return {
        "id": job_id,
        "institution_id": "inst-1",
        "course_id": "course-1",
        "skill_id": "skill-1",
        "kind": "practice",
        "set_id": "set-1",
        "context_offset": offset,
        "status": status,
        "attempt_count": attempt_count,
        "next_attempt_at": datetime.now(UTC).isoformat(),
        "started_at": started_at or datetime.now(UTC).isoformat(),
    }


def _lesson_row(job_id="lesson-job", *, status="pending"):
    row = _row(job_id, status=status)
    row.update({
        "kind": "lesson", "set_id": None, "lesson_step_id": "step-1",
    })
    return row


def test_claims_at_most_two_eligible_rows_and_preserves_offsets(monkeypatch):
    fake = FakeDB([_row("j1", offset=0), _row("j2", offset=1), _row("j3", offset=2)])
    monkeypatch.setattr(item_generation, "db", fake)
    seen_offsets = []

    def fake_generate(**kwargs):
        seen_offsets.append(kwargs["context_offset"])
        return {"id": kwargs["job_id"]}

    monkeypatch.setattr(item_generation, "generate_question", fake_generate)

    result = item_generation.run()

    assert result["claimed"] == 2
    assert result["completed"] == 2
    assert sorted(seen_offsets) == [0, 1]
    assert all(row["status"] == "pending" for row in fake.rows[2:])


def test_transport_failure_uses_the_first_backoff_and_keeps_queue_pending(monkeypatch):
    fake = FakeDB([_row("j1")])
    monkeypatch.setattr(item_generation, "db", fake)

    def fail(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(item_generation, "generate_question", fail)

    result = item_generation.run()

    assert result["retrying"] == 1
    assert fake.rows[0]["status"] == "pending"
    assert fake.rows[0]["attempt_count"] == 1
    retry_at = datetime.fromisoformat(fake.rows[0]["next_attempt_at"])
    assert retry_at >= datetime.now(UTC) + timedelta(minutes=14)


def test_fifth_failure_becomes_terminal_without_answer_data(monkeypatch):
    fake = FakeDB([_row("j1", attempt_count=4)])
    monkeypatch.setattr(item_generation, "db", fake)
    monkeypatch.setattr(item_generation, "generate_question", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))

    result = item_generation.run()

    assert result["failed"] == 1
    assert fake.rows[0]["status"] == "failed"
    assert "correct_choice_id" not in fake.rows[0]
    assert "explanation" not in fake.rows[0]


def test_persisted_item_is_reconciled_without_a_second_model_call(monkeypatch):
    fake = FakeDB([_row("j1")], existing_ids={"j1"})
    monkeypatch.setattr(item_generation, "db", fake)
    monkeypatch.setattr(
        item_generation, "generate_question",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not regenerate")),
    )

    result = item_generation.run()

    assert result["reconciled"] == 1
    assert fake.rows[0]["status"] == "complete"
    assert fake.rows[0]["item_id"] == "j1"


def test_pickup_query_contains_backoff_deadline_and_status(monkeypatch):
    class QueryDB(FakeDB):
        def select(self, table, params):
            if table == "item_generation_jobs":
                if params["status"] == "eq.in_progress":
                    return []
                assert params["status"] == "eq.pending"
                assert params["next_attempt_at"].startswith("lte.")
                assert params["order"] == "next_attempt_at.asc"
                assert params["limit"] == "2"
                return []
            return super().select(table, params)

    monkeypatch.setattr(item_generation, "db", QueryDB([]))
    result = item_generation.run(institution_id="inst-1")
    assert result["claimed"] == 0


def test_reclaim_stale_in_progress_row_returns_it_to_pending(monkeypatch):
    started_at = datetime.now(UTC) - timedelta(seconds=item_generation._STALE_AFTER_SECONDS + 1)
    fake = FakeDB([_row("j1", status="in_progress", started_at=started_at.isoformat())])
    monkeypatch.setattr(item_generation, "db", fake)

    assert item_generation._reclaim_stale(institution_id=None) == 1
    assert fake.rows[0]["status"] == "pending"
    assert datetime.fromisoformat(fake.rows[0]["next_attempt_at"]) >= datetime.now(UTC) - timedelta(seconds=2)


def test_reclaim_does_not_reset_recent_in_progress_row(monkeypatch):
    started_at = datetime.now(UTC) - timedelta(seconds=item_generation._STALE_AFTER_SECONDS - 1)
    fake = FakeDB([_row("j1", status="in_progress", started_at=started_at.isoformat())])
    monkeypatch.setattr(item_generation, "db", fake)

    assert item_generation._reclaim_stale(institution_id=None) == 0
    assert fake.rows[0]["status"] == "in_progress"
    assert fake.updates == []


def test_lesson_success_updates_tenant_verified_step_before_checkpoint(monkeypatch):
    fake = LessonDB([_lesson_row()])
    monkeypatch.setattr(item_generation, "db", fake)
    seen = []

    def generate(**kwargs):
        seen.append(kwargs)
        return {"id": kwargs["job_id"]}

    monkeypatch.setattr(item_generation, "generate_question", generate)

    result = item_generation.run()

    assert result["completed"] == 1
    assert seen[0]["kind"] == "tutor"
    assert fake.step["check_item_id"] == "lesson-job"
    assert fake.rows[0]["status"] == "complete"
    assert fake.rows[0]["item_id"] == "lesson-job"


def test_lesson_tenant_mismatch_does_not_checkpoint(monkeypatch):
    fake = LessonDB([_lesson_row()])
    monkeypatch.setattr(item_generation, "db", fake)

    def wrong_tenant_select(table, params):
        if table == "guided_lesson_steps":
            return []
        return fake.select(table, params)

    monkeypatch.setattr(item_generation, "db", type("DB", (), {
        "select": staticmethod(wrong_tenant_select),
        "update": staticmethod(fake.update),
    })())
    monkeypatch.setattr(item_generation, "generate_question", lambda **kwargs: {"id": kwargs["job_id"]})

    result = item_generation.run()

    assert result["retrying"] == 1
    assert fake.rows[0]["status"] == "pending"
    assert fake.step["check_item_id"] is None
