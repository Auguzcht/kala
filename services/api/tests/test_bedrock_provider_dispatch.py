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


def test_openrouter_input_type_maps_bedrock_vocabulary():
    """OpenRouter's NVIDIA embedding endpoint uses passage/query, not
    Bedrock's search_document/search_query. Live-tested: an unmapped value
    400s, and omitting the field entirely 500s, so this mapping is load-
    bearing, not cosmetic."""
    assert bedrock._to_openrouter_input_type("search_document") == "passage"
    assert bedrock._to_openrouter_input_type("search_query") == "query"


def test_openrouter_input_type_defaults_unknown_values_to_passage():
    """An unrecognized input_type must never be forwarded as-is (known to
    400) and must never be omitted (known to 500 for this provider)."""
    assert bedrock._to_openrouter_input_type("something_new") == "passage"


def test_openrouter_embed_sends_mapped_input_type(monkeypatch):
    """The actual request body must carry the mapped value, not the raw
    Bedrock-style one, this is the exact bug DeepSeek's live test caught."""
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "openrouter", "openrouter_embed_model": "m",
        "openrouter_base_url": "https://example.test", "openrouter_api_key": "k",
    })())

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [0.0] * 1024}]}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, path, json):
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: FakeClient())
    bedrock._openrouter_embed("hello", input_type="search_document")
    assert captured["body"]["input_type"] == "passage"


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
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "openrouter", "embed_provider": "",
    })())
    monkeypatch.setattr(bedrock, "_openrouter_embed", lambda text, **k: [0.1] * 1024)
    assert bedrock.embed("hello") == [0.1] * 1024


def test_embed_provider_overrides_ai_provider_independently(monkeypatch):
    """Chat can stay on OpenRouter while embeddings go to OpenAI, the two
    are independent settings on purpose (found necessary live: OpenRouter's
    free chat models worked fine while its free embed endpoint 500'd)."""
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "openrouter", "embed_provider": "openai",
    })())
    monkeypatch.setattr(bedrock, "_openai_embed", lambda text, **k: [0.2] * 1024)
    assert bedrock.embed("hello") == [0.2] * 1024


def test_embed_falls_back_to_ai_provider_when_embed_provider_unset(monkeypatch):
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "bedrock", "embed_provider": "",
    })())
    monkeypatch.setattr(bedrock, "_bedrock_embed", lambda text, **k: [0.3] * 1024)
    assert bedrock.embed("hello") == [0.3] * 1024


def test_openai_embed_requests_1024_dimensions_directly(monkeypatch):
    """OpenAI supports requesting a smaller output natively; no manual
    truncation needed for this provider, unlike the NVIDIA/OpenRouter path."""
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "openai_api_key": "k", "openai_base_url": "https://example.test",
        "openai_embed_model": "text-embedding-3-small",
    })())
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [0.0] * 1024}]}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, path, json):
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(bedrock, "_openai_client", lambda: FakeClient())
    out = bedrock._openai_embed("hello", input_type="search_document")
    assert len(out) == 1024
    assert captured["body"]["dimensions"] == 1024
    assert captured["body"]["model"] == "text-embedding-3-small"
