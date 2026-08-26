import math

from app.ai import bedrock


def test_truncate_and_renormalize_shrinks_to_target_dims():
    vec = [1.0] * 2048
    out = bedrock._truncate_and_renormalize(vec, dims=1024)
    assert len(out) == 1024


def test_truncate_and_renormalize_is_unit_length():
    vec = [3.0, 4.0] + [0.0] * 2046  # 2050-length, first two form a 3-4-5 triangle
    out = bedrock._truncate_and_renormalize(vec[:2048], dims=2)
    norm = math.sqrt(sum(x * x for x in out))
    assert abs(norm - 1.0) < 1e-9


def test_truncate_and_renormalize_passes_through_when_already_short_enough():
    vec = [0.1, 0.2, 0.3]
    assert bedrock._truncate_and_renormalize(vec, dims=1024) == vec


def test_truncate_and_renormalize_handles_degenerate_zero_vector():
    out = bedrock._truncate_and_renormalize([0.0] * 2048, dims=1024)
    assert out == [0.0] * 1024  # no division-by-zero crash


def test_flatten_text_extracts_from_bedrock_shaped_content():
    content = [{"text": "hello "}, {"text": "world"}]
    assert bedrock._flatten_text(content) == "hello world"


def test_flatten_text_passes_through_plain_string():
    assert bedrock._flatten_text("already a string") == "already a string"


def test_converse_dispatches_to_openrouter_when_configured(monkeypatch):
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {"ai_provider": "openrouter"})())
    called = {}

    def fake_openrouter_converse(*, model_id, system, messages, max_tokens):
        called["hit"] = True
        return "ok"

    monkeypatch.setattr(bedrock, "_openrouter_converse", fake_openrouter_converse)
    result = bedrock.converse(model_id="m", system="s", messages=[{"role": "user", "content": [{"text": "hi"}]}])
    assert result == "ok"
    assert called["hit"] is True


def test_converse_dispatches_to_bedrock_by_default(monkeypatch):
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {"ai_provider": "bedrock"})())
    called = {}

    def fake_bedrock_converse(*, model_id, system, messages, max_tokens):
        called["hit"] = True
        return "ok"

    monkeypatch.setattr(bedrock, "_bedrock_converse", fake_bedrock_converse)
    result = bedrock.converse(model_id="m", system="s", messages=[{"role": "user", "content": [{"text": "hi"}]}])
    assert result == "ok"
    assert called["hit"] is True


def test_embed_dispatches_by_provider(monkeypatch):
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {"ai_provider": "openrouter"})())
    monkeypatch.setattr(bedrock, "_openrouter_embed", lambda text, **k: [0.1] * 1024)
    assert bedrock.embed("hello") == [0.1] * 1024
