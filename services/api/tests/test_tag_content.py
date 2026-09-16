"""tag_content — the ingest tagging call.

Found by running ingest against the real course and noticing almost nothing
tagged. Root cause was NOT the prompt or the model: tag_content asked for
max_tokens=256 while the model reasons before answering, and its thinking is
billed against that budget. Measured 330-550 reasoning tokens per chunk, so the
response was truncated mid-thought and came back empty EVERY time, which
json.loads rejected and the function reported as skill_id=None.

A 4000-char module page about cloud computing returned null against a skill
named "Compare and contrast traditional IT infrastructure with cloud computing
models". Verified directly: the identical request at 1500 tokens returns the
correct skill_id. These tests pin the budget and the parse behaviour.
"""
import json

from app.ai import router as model_router


def _capture_converse(monkeypatch, canned: str):
    captured = {}

    def fake_converse(**kwargs):
        captured.update(kwargs)
        return canned

    monkeypatch.setattr(model_router.bedrock, "converse", fake_converse)
    monkeypatch.setattr(model_router, "get_model_for", lambda task: "tag-model")
    return captured


SKILLS = [{"id": "skill-1", "name": "Cloud concepts"},
          {"id": "skill-2", "name": "AWS service categories"}]


def test_tag_content_allows_a_reasoning_budget_large_enough_to_answer(monkeypatch) -> None:
    """The bug, twice over. This model reasons before answering and its thinking
    is billed against max_tokens. At 256 every response was truncated to empty
    and read as "no match". At 2048 short chunks worked but long module pages
    still hit finish_reason=length — a fix that looked complete while silently
    still failing on the most valuable content. A 3145-char module page needs
    ~2500-3500 reasoning tokens, so 4096 is the measured floor."""
    captured = _capture_converse(
        monkeypatch, json.dumps({"skill_id": "skill-1", "bloom_level": "understand"})
    )
    model_router.tag_content(text="Cloud computing is...", skills=SKILLS)

    assert captured["max_tokens"] >= 4096, (
        "tag_content's token budget must cover the model's reasoning on a LONG "
        "chunk (~3000 tokens), or the JSON answer is truncated away and the "
        "result reads as 'no match'"
    )


def test_tag_content_parses_a_valid_match(monkeypatch) -> None:
    _capture_converse(
        monkeypatch, json.dumps({"skill_id": "skill-1", "bloom_level": "apply"})
    )
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out == {"skill_id": "skill-1", "bloom_level": "apply"}


def test_tag_content_rejects_a_skill_id_not_in_the_candidate_list(monkeypatch) -> None:
    """A hallucinated or stale id must not be written to the row."""
    _capture_converse(
        monkeypatch, json.dumps({"skill_id": "skill-999", "bloom_level": "apply"})
    )
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out["skill_id"] is None


def test_tag_content_rejects_an_invalid_bloom_level(monkeypatch) -> None:
    _capture_converse(
        monkeypatch, json.dumps({"skill_id": "skill-1", "bloom_level": "vibes"})
    )
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out["skill_id"] == "skill-1"
    assert out["bloom_level"] is None


def test_tag_content_tolerates_a_fenced_response(monkeypatch) -> None:
    _capture_converse(
        monkeypatch, '```json\n{"skill_id": "skill-2", "bloom_level": "remember"}\n```'
    )
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out["skill_id"] == "skill-2"


def test_tag_content_reports_no_match_on_an_empty_response(monkeypatch) -> None:
    """Still degrades to no-match (a truncated response must not crash ingest),
    but it now logs, because an empty body and a genuine no-match are
    indistinguishable in the return value — which is what hid the bug."""
    _capture_converse(monkeypatch, "")
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out == {"skill_id": None, "bloom_level": None}


def test_tag_content_reports_no_match_on_unparseable_json(monkeypatch) -> None:
    _capture_converse(monkeypatch, "not json at all")
    out = model_router.tag_content(text="x", skills=SKILLS)
    assert out == {"skill_id": None, "bloom_level": None}
