from __future__ import annotations

import time

import pytest

from app import item_gen


def _skill():
    return {"id": "skill-1", "name": "Cloud concepts", "bloom_level": "understand"}


def _answer():
    return "What is cloud computing?", [
        {"id": "a", "label": "On-demand computing"},
        {"id": "b", "label": "A printed manual"},
        {"id": "c", "label": "A local cable"},
        {"id": "d", "label": "A paper ledger"},
    ], "a", "Cloud computing provides on-demand resources."


def test_worker_validation_reroll_is_gated_by_remaining_budget(monkeypatch):
    calls = []

    def scripted_call(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise ValueError("bad validation")
        return _answer()

    inserted = []
    monkeypatch.setattr(item_gen, "_context_for", lambda **kwargs: ["grounded chunk"])
    monkeypatch.setattr(item_gen, "_call_and_validate", scripted_call)
    monkeypatch.setattr(item_gen.db, "insert", lambda table, rows: inserted.extend(rows) or rows)

    result = item_gen.generate_question(
        institution_id="inst-1", course_id="course-1", skill=_skill(),
        kind="practice", job_id="job-1", set_id="set-1", context_offset=2,
        deadline=time.monotonic() + 100, call_timeout_seconds=90,
    )

    assert len(calls) == 2
    assert result["id"] == "job-1"
    assert "correct_choice_id" not in result
    assert "explanation" not in result
    assert inserted[0]["correct_choice_id"] == "a"
    assert inserted[0]["explanation"]
    assert inserted[0]["set_id"] == "set-1"


def test_worker_does_not_reroll_when_budget_is_below_gate(monkeypatch):
    calls = []

    def invalid_call(**kwargs):
        calls.append(kwargs)
        raise ValueError("bad validation")

    monkeypatch.setattr(item_gen, "_context_for", lambda **kwargs: ["grounded chunk"])
    monkeypatch.setattr(item_gen, "_call_and_validate", invalid_call)

    with pytest.raises(item_gen.ItemGenerationError):
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=_skill(),
            kind="diagnostic", job_id="job-1", deadline=time.monotonic() + 50,
            call_timeout_seconds=90,
        )

    assert len(calls) == 1


def test_empty_retrieval_raises_retryable_no_content(monkeypatch):
    monkeypatch.setattr(item_gen, "_context_for", lambda **kwargs: (_ for _ in ()).throw(
        item_gen.NoCourseContentError(skill_name="Cloud concepts")
    ))

    with pytest.raises(item_gen.NoCourseContentError):
        item_gen.generate_question(
            institution_id="inst-1", course_id="course-1", skill=_skill(),
            kind="diagnostic", job_id="job-1", deadline=time.monotonic() + 100,
            call_timeout_seconds=90,
        )
