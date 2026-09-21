import math

from app.ai import bedrock
from app.ai.errors import ModelUnavailableError


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


def test_openrouter_converse_retries_a_transient_failure_with_fallback(monkeypatch):
    """A listed free model can still have an unavailable provider. The
    fallback must be a one-shot retry on a separately configured model, not an
    unbounded retry loop that runs through Lambda's gateway timeout."""
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "openrouter",
        "openrouter_model_fallback": "fallback-model",
    })())
    attempted = []

    def fake_openrouter_converse(*, model_id, system, messages, max_tokens):
        attempted.append(model_id)
        if model_id == "primary-model":
            raise ModelUnavailableError(
                "provider unavailable", provider="openrouter", model_id=model_id, status_code=503,
            )
        return "fallback answer"

    monkeypatch.setattr(bedrock, "_openrouter_converse", fake_openrouter_converse)
    result = bedrock.converse(
        model_id="primary-model", system="s", messages=[{"role": "user", "content": [{"text": "hi"}]}],
    )
    assert result == "fallback answer"
    assert attempted == ["primary-model", "fallback-model"]


def test_openrouter_converse_sends_structured_output_contract(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "{\"prompt\": \"Q\"}"}}]}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, path, json):
            captured["path"] = path
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: FakeClient())
    response_format = {"type": "json_schema", "json_schema": {"name": "study_question"}}
    result = bedrock._openrouter_converse(
        model_id="model",
        system="system",
        messages=[{"role": "user", "content": [{"text": "prompt"}]}],
        max_tokens=100,
        response_format=response_format,
    )

    assert result == '{"prompt": "Q"}'
    assert captured["path"] == "/chat/completions"
    assert captured["body"]["response_format"] == response_format
    # Deliberately NO provider.require_parameters: it hard-404s models whose
    # endpoints don't advertise the parameter even when they can answer (live:
    # cohere/north-mini-code:free, inclusionai/*). A model that ignores the
    # schema instead returns JSON that _validated_mcq rejects and retries, so
    # "try it and validate" beats "refuse to try".
    #
    # Asserted on require_parameters rather than on the whole `provider` key:
    # a `provider` block IS present now, but only for routing preference
    # (order + allow_fallbacks), which is a different thing. The old blanket
    # `"provider" not in body` was a proxy for this intent and would now fail
    # for the wrong reason.
    provider_block = captured["body"].get("provider") or {}
    assert "require_parameters" not in provider_block
    # And routing must never hard-pin: allow_fallbacks stays true so a busy
    # preferred provider falls through instead of 503ing.
    if provider_block:
        assert provider_block.get("allow_fallbacks") is True


def test_openrouter_converse_does_not_retry_a_bad_api_key(monkeypatch):
    monkeypatch.setattr(bedrock, "get_settings", lambda: type("S", (), {
        "ai_provider": "openrouter",
        "openrouter_model_fallback": "fallback-model",
    })())
    attempted = []

    def fake_openrouter_converse(*, model_id, system, messages, max_tokens):
        attempted.append(model_id)
        raise ModelUnavailableError(
            "bad key", provider="openrouter", model_id=model_id, status_code=401,
        )

    monkeypatch.setattr(bedrock, "_openrouter_converse", fake_openrouter_converse)
    try:
        bedrock.converse(
            model_id="primary-model", system="s", messages=[{"role": "user", "content": [{"text": "hi"}]}],
        )
    except ModelUnavailableError:
        pass
    else:
        raise AssertionError("the 401 must not be retried")
    assert attempted == ["primary-model"]


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


# ---- structured-output capability degradation ----------------------------
# Reproduced live (2026-09-16): a model whose providers don't advertise
# json_schema returns 404 {"No endpoints found that can handle the requested
# parameters"} when response_format + provider.require_parameters are sent.
# Free-tier models churn, so this must degrade to prompt-enforced JSON instead
# of failing the request — otherwise every model retirement re-breaks item
# generation.


def _settings(provider="openrouter", model_item="m", fallback=""):
    return type("S", (), {
        "ai_provider": provider, "openrouter_model_fallback": fallback,
        "openrouter_base_url": "https://example.test", "openrouter_api_key": "k",
    })()


def _routes(handler):
    """Build a fake client whose post() delegates to `handler(payload)`,
    returning either a json body or raising an httpx.HTTPStatusError."""
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, path, json):
            return handler(json)

    return FakeClient()


def _resp(payload):
    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return payload
    return R()


def _err(status, body):
    import httpx

    class R:
        status_code = status
        text = body

        def raise_for_status(self):
            raise httpx.HTTPStatusError("err", request=None, response=self)

        def json(self):
            return {}
    return R()


def test_is_provider_parameter_rejection_distinguishes_404_causes():
    assert bedrock._is_provider_parameter_rejection(
        '{"error":{"message":"No endpoints found that can handle the requested '
        'parameters. To learn more about provider routing, visit: ..."}}'
    )
    # An unknown/retired model is ALSO a 404 but must NOT be treated as a
    # degradable capability gap.
    assert not bedrock._is_provider_parameter_rejection(
        '{"error":{"message":"No endpoints found for google/x:free."}}'
    )


def test_structured_request_degrades_when_provider_rejects_parameters(monkeypatch):
    """First attempt (with response_format) 404s on the routing filter; the
    retry without it must succeed and the content must come back."""
    attempts = []

    def handler(payload):
        attempts.append(payload)
        if "response_format" in payload:
            return _err(404, '{"error":{"message":"No endpoints found that can '
                             'handle the requested parameters. To learn more '
                             'about provider routing, visit: x"}}')
        return _resp({"choices": [{"message": {"content": '{"prompt":"ok"}'}}]})

    monkeypatch.setattr(bedrock, "get_settings", lambda: _settings())
    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: _routes(handler))

    out = bedrock._openrouter_converse(
        model_id="m", system="s", messages=[{"role": "user", "content": [{"text": "u"}]}],
        max_tokens=100, response_format={"type": "json_schema"},
    )

    assert out == '{"prompt":"ok"}'
    assert len(attempts) == 2
    assert "response_format" in attempts[0]
    assert "response_format" not in attempts[1]
    # The degradation retry must also drop require_parameters — that filter is
    # what produced the 404, and there is no schema to require without a format.
    assert "provider" not in attempts[1]


def test_unknown_model_404_does_not_retry(monkeypatch):
    """A retired model id is fatal — retrying cannot help, so it must surface
    as ModelUnavailableError after ONE attempt, not loop."""
    attempts = []

    def handler(payload):
        attempts.append(payload)
        return _err(404, '{"error":{"message":"No endpoints found for x:free."}}')

    monkeypatch.setattr(bedrock, "get_settings", lambda: _settings())
    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: _routes(handler))

    try:
        bedrock._openrouter_converse(
            model_id="x:free", system="s",
            messages=[{"role": "user", "content": [{"text": "u"}]}],
            max_tokens=100, response_format={"type": "json_schema"},
        )
        assert False, "expected ModelUnavailableError"
    except ModelUnavailableError as exc:
        assert exc.model_not_found is True

    assert len(attempts) == 1


def test_openrouter_content_tolerates_null_and_empty_choices():
    """A model that emits only a reasoning field, or no choices at all, must
    yield '' — not a KeyError that surfaces as an opaque parse failure."""
    assert bedrock._openrouter_content({"choices": [{"message": {"content": None}}]}) == ""
    assert bedrock._openrouter_content({"choices": []}) == ""
    assert bedrock._openrouter_content({}) == ""


def test_provider_order_is_sent_as_a_preference_never_a_hard_pin(monkeypatch):
    """OpenRouter load-balances one model id across ~15 providers whose
    latencies differ by ~20x (measured: unpinned 32/64/113s vs pinned 2.8-8.5s
    on the same prompt). That spread is what pushed tutor requests past the
    30s Lambda wall.

    The fix is a PREFERENCE with fallbacks left ON. A hard pin would trade a
    slow success for a fast failure: a busy preferred provider would 503 where
    the unpinned path would simply have used another one. So this pins the
    exact shape that matters — order present, allow_fallbacks true — and not
    merely that a provider key exists.
    """
    import app.ai.bedrock as bedrock

    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    def fake_post(path, json=None):
        captured.update(json or {})
        return _Resp()

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, path, json=None):
            return fake_post(path, json=json)

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: _Client())
    monkeypatch.setattr(
        bedrock, "get_settings",
        lambda: type("S", (), {"openrouter_provider_order": "Relace,DeepInfra"})(),
    )

    bedrock._openrouter_post(
        model_id="m", messages=[], max_tokens=10, response_format=None,
    )

    assert captured["provider"]["order"] == ["Relace", "DeepInfra"]
    assert captured["provider"]["allow_fallbacks"] is True


def test_an_empty_provider_order_sends_no_provider_block(monkeypatch):
    """The escape hatch: blanking OPENROUTER_PROVIDER_ORDER must restore
    exactly the previous behavior, so this can be switched off in config
    without a code change if the provider mix shifts."""
    import app.ai.bedrock as bedrock

    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, path, json=None):
            captured.update(json or {})
            return _Resp()

    monkeypatch.setattr(bedrock, "_openrouter_client", lambda: _Client())
    monkeypatch.setattr(
        bedrock, "get_settings",
        lambda: type("S", (), {"openrouter_provider_order": ""})(),
    )

    bedrock._openrouter_post(
        model_id="m", messages=[], max_tokens=10, response_format=None,
    )

    assert "provider" not in captured
