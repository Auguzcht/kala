"""E1 / TUTOR-REQ-013: inspect the actual provider-bound prompt offline."""
from functools import partial

import anyio
import pytest

from app.ai import bedrock
from app.deps import CurrentUser
from app.routers import tutor
from conftest import COURSE_ID, INSTITUTION_ID, USER_ID


@pytest.mark.parametrize("question,style", [("Hello!", "default"), ("Thanks!", "detail")])
def test_small_talk_rule_reaches_provider_with_retained_safety(monkeypatch, question, style):
    captured = []
    monkeypatch.setattr(tutor.rag, "retrieve", lambda **kwargs: [{"chunk_text": "Synthetic course material"}])
    monkeypatch.setattr(tutor.model_router, "get_model_for", lambda _: "synthetic-chat")
    monkeypatch.setattr(tutor.model_router, "get_fallback_for", lambda _: "synthetic-fallback")

    def converse(**kwargs):
        captured.append(kwargs)
        return "Hello! How can I help?"

    monkeypatch.setattr(bedrock, "converse", converse)
    result = anyio.run(partial(tutor.ask, tutor.Ask(course_id=COURSE_ID, question=question, style=style),
        CurrentUser(user_id=USER_ID, institution_id=INSTITUTION_ID, app_role="student")))

    assert result == {"answer": "Hello! How can I help?"}
    assert len(captured) == 1
    prompt = captured[0]["system"]
    assert "greeting or a message with no course question" in prompt
    assert "brief, friendly reply" in prompt and "offer to help" in prompt
    assert "Do not give a study roadmap or mention 'course context'" in prompt
    assert "Never reveal answers to graded work" in prompt
    assert "do not narrate your reasoning" in prompt
    assert "For actual course questions, retain course grounding and all graded-work protections" in prompt
    assert prompt.endswith(tutor._STYLE_HINTS[style])
    assert "Synthetic course material" in captured[0]["messages"][-1]["content"][0]["text"]
