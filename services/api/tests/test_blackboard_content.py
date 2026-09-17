"""Tests for the Blackboard content extraction fixes.

Both bugs here were found by auditing why generated questions were meaningless
(not by a failing test): the connector stored HTML as if it were content, and
it only walked a fraction of the course tree. The narrow functions are tested
directly; the live tree shape is verified by the ingest diagnostic log, since
it depends on a real Blackboard instance this suite cannot reach.
"""
from unittest.mock import patch

import httpx

from app.config import Settings
from app.lms.blackboard import BlackboardConnector, BlackboardRateLimitedError, _to_plain_text


# ---- HTML/BBML -> plain text ---------------------------------------------


def test_plain_text_passes_through_with_whitespace_normalised():
    assert _to_plain_text("  Photosynthesis   converts  light.  ") == "Photosynthesis converts light."


def test_bbml_markup_is_stripped_to_words():
    """The live Vision/Mission page arrives as wrapper divs + span styles
    around a few sentences. Storing or sending that markup is the bug."""
    raw = (
        '<div data-bbid="bbml-editor-id_x"><h4 style="text-align:center;">'
        '<span style="font-size:1.5rem;"><strong>Vision</strong></span></h4>'
        '<p style="text-align:center;"><span style="color:#222222">'
        'The institute stands among the world\'s leading institutions.</span></p></div>'
    )
    out = _to_plain_text(raw)
    assert "Vision" in out
    assert "leading institutions" in out
    assert "<" not in out and ">" not in out
    assert "data-bbid" not in out
    assert "text-align" not in out


def test_block_tags_become_line_breaks_so_words_do_not_run_together():
    raw = "<p>First sentence.</p><p>Second sentence.</p>"
    out = _to_plain_text(raw)
    assert "First sentence." in out
    assert "Second sentence." in out
    # The paragraphs must be separated, not fused into one run-on line.
    assert "First sentence.\n" in out
    assert "sentence.Second" not in out


def test_script_and_style_content_is_dropped():
    raw = "<p>Real text</p><script>var x = 1;</script><style>.a{color:red}</style>"
    out = _to_plain_text(raw)
    assert "Real text" in out
    assert "var x" not in out
    assert "color:red" not in out


def test_non_breaking_spaces_are_normalised():
    assert _to_plain_text("Excellence&nbsp;and&nbsp;Relevance") == "Excellence and Relevance"


def test_entities_are_decoded():
    out = _to_plain_text("<p>Research &amp; development</p>")
    assert "Research & development" in out


def test_malformed_markup_still_yields_the_words():
    """A broken body must never abort an ingest run."""
    out = _to_plain_text("<p>Unclosed paragraph <b>bold text")
    assert "Unclosed paragraph" in out
    assert "bold text" in out


def test_empty_input_is_empty():
    assert _to_plain_text("") == ""
    assert _to_plain_text(None) == ""


# ---- tree traversal -------------------------------------------------------


class _Response:
    """Minimal stand-in for httpx.Response.

    Carries status_code/headers/request because _check_rate_limit reads all
    three on EVERY connector call (quota logging + the 429 check). A fake
    without them would make the connector raise AttributeError, i.e. the tests
    would fail for a reason that cannot happen against a real HTTP response.
    """

    def __init__(self, payload, *, status_code: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.request = httpx.Request("GET", "https://learn.example/learn/api/public/v1/test")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=self.request, response=self,
            )

    def json(self):
        return self._payload


def _connector(root_results, children_by_id):
    settings = Settings(
        LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
        LMS_VERIFY_TLS=False,
    )
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    def fake_get(path, **kwargs):
        # children endpoint ends with /<id>/children
        if path.endswith("/children"):
            parent = path.rstrip("/").split("/")[-2]
            return _Response({"results": children_by_id.get(parent, [])})
        return _Response({"results": root_results})

    return connector, settings, fake_get


def test_content_walks_children_of_a_container_even_without_haschildren():
    """The live course yielded 5 items, all from one branch, because recursion
    depended on `hasChildren` being set. Containers are now descended by their
    handler type too, so a module tree is actually walked."""
    root = [{"id": "_1_1", "title": "Course", "contentHandler": {"id": "resource/x-bb-folder"}}]
    children = {
        "_1_1": [
            {"id": "_2_1", "title": "Module 2", "contentHandler": {"id": "resource/x-bb-lesson"}},
        ],
        "_2_1": [
            {"id": "_3_1", "title": "AWS page", "body": "<p>Managed services trade cost for ops.</p>",
             "contentHandler": {"id": "resource/x-bb-document"}},
        ],
    }
    connector, settings, fake_get = _connector(root, children)
    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ):
        items = connector.get_content("_course_1")

    ids = [i["lms_content_id"] for i in items]
    assert "_3_1" in ids, "the nested AWS page must be reached"
    nested = next(i for i in items if i["lms_content_id"] == "_3_1")
    # And its HTML body arrives as plain text.
    assert nested["body_or_description"] == "Managed services trade cost for ops."


def test_content_does_not_revisit_a_node_reported_twice():
    """A tree that exposes children both via hasChildren and via handler type
    must not fetch (or store) the same node twice."""
    root = [
        {"id": "_1_1", "title": "A", "hasChildren": True,
         "contentHandler": {"id": "resource/x-bb-folder"}, "body": "alpha"},
        {"id": "_1_1", "title": "A duplicate row", "body": "alpha"},
    ]
    connector, settings, fake_get = _connector(root, {})
    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ):
        items = connector.get_content("_course_1")

    assert [i["lms_content_id"] for i in items].count("_1_1") == 1


def test_content_survives_a_failing_subtree():
    """One unreadable subtree must not lose the rest of the course."""
    import httpx

    root = [
        {"id": "_1_1", "title": "Good", "contentHandler": {"id": "resource/x-bb-folder"}},
        {"id": "_2_1", "title": "Has body", "body": "kept",
         "contentHandler": {"id": "resource/x-bb-document"}},
    ]
    settings = Settings(
        LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1", LMS_VERIFY_TLS=False,
    )
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    def raise_http(path, **kwargs):
        if path.endswith("/children"):
            raise httpx.ConnectError("boom")
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=raise_http
    ):
        items = connector.get_content("_course_1")

    ids = [i["lms_content_id"] for i in items]
    assert "_2_1" in ids, "sibling content survives a failing subtree"


def test_description_is_used_only_when_body_is_absent():
    root = [
        {"id": "_1_1", "title": "Has body", "body": "<p>real body</p>", "description": "desc",
         "contentHandler": {"id": "resource/x-bb-document"}},
        {"id": "_2_1", "title": "Only desc", "description": "only a description",
         "contentHandler": {"id": "resource/x-bb-document"}},
    ]
    connector, settings, fake_get = _connector(root, {})
    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ):
        items = {i["lms_content_id"]: i for i in connector.get_content("_course_1")}

    assert items["_1_1"]["body_or_description"] == "real body"
    assert items["_2_1"]["body_or_description"] == "only a description"


# ---- rate limiting (quota exhaustion) -------------------------------------
#
# The dev instance burned its 10,000-request quota during ordinary testing
# (Retry-After: 20807s, X-Rate-Limit-Remaining: 0) and every launch failed
# until the window reset. There was no 429 handling anywhere: raise_for_status
# threw a generic HTTPStatusError straight through. These pin the replacement:
# a distinct, retry-after-carrying exception and no blind retry.


def _rate_limit_settings():
    return Settings(
        LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
        LMS_VERIFY_TLS=False,
    )


def test_resolve_course_ref_raises_a_distinct_error_on_429_without_retrying():
    """A 429 must surface as BlackboardRateLimitedError carrying the retry-after,
    and must NOT be retried. X-Rate-Limit-Remaining: 0 means an immediate retry
    is guaranteed to fail and costs another request against a zero quota."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}
    calls: list[str] = []

    def fake_get(path, **kwargs):
        calls.append(path)
        return _Response(
            {"error": "rate limited"}, status_code=429,
            headers={"Retry-After": "20807", "X-Rate-Limit-Remaining": "0"},
        )

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ):
        try:
            connector.resolve_course_ref("ME301")
            assert False, "expected BlackboardRateLimitedError"
        except BlackboardRateLimitedError as exc:
            assert exc.retry_after == 20807
            assert "rate limited" in str(exc).lower()

    assert len(calls) == 1, "a 429 must not be retried — the quota is already at zero"


def test_the_live_blackboard_retry_after_format_parses():
    """Pinned to the REAL header from the incident: the live instance sends
    `Retry-After: 20807s` with a trailing unit, which the RFC does not define
    and a bare int() parse rejects. Parsing it wrong would silently downgrade
    the 502's message from "retry after roughly 20807 seconds" to "when the
    window resets" — on the one response this code exists to read."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response(
            {"status": 429, "message": "Unauthorized"}, status_code=429,
            headers={
                # Exactly as captured from the dev instance on 2026-09-17.
                "Retry-After": "20807s",
                "X-Rate-Limit-Limit": "10000",
                "X-Rate-Limit-Remaining": "0",
            },
        ),
    ):
        try:
            connector.resolve_course_ref("AWS101.A321.1T.27.28")
            assert False, "expected BlackboardRateLimitedError"
        except BlackboardRateLimitedError as exc:
            assert exc.retry_after == 20807


def test_a_429_without_retry_after_still_raises_cleanly():
    """The header is optional in the spec. Its absence must degrade to a None
    retry_after, not to a crash or a swallowed error."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response({"error": "rate limited"}, status_code=429),
    ):
        try:
            connector.resolve_course_ref("ME301")
            assert False, "expected BlackboardRateLimitedError"
        except BlackboardRateLimitedError as exc:
            assert exc.retry_after is None


def test_an_rfc_style_http_date_retry_after_does_not_crash():
    """The spec's other legal form. Blackboard does not send it today, but an
    upgrade could, and the response must degrade to None rather than raising
    inside error handling."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response(
            {}, status_code=429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        ),
    ):
        try:
            connector.resolve_course_ref("ME301")
            assert False, "expected BlackboardRateLimitedError"
        except BlackboardRateLimitedError as exc:
            # No digits at the start, so no delta is derived — but the caller
            # still gets the specific error type, not an HTTPStatusError.
            assert exc.retry_after is None


def test_get_roster_propagates_the_rate_limit_instead_of_a_generic_error():
    """Every call site must get the typed error, not just resolve_course_ref —
    the roster pull is the multi-request path that burns quota fastest."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response(
            {}, status_code=429, headers={"Retry-After": "60"},
        ),
    ):
        try:
            connector.get_roster("_course_1")
            assert False, "expected BlackboardRateLimitedError"
        except BlackboardRateLimitedError as exc:
            assert exc.retry_after == 60


def test_a_low_remaining_quota_logs_a_warning(caplog):
    """The cheap early-warning signal that would have caught today's exhaustion
    before it became a launch-blocking outage."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response(
            {"results": []}, status_code=200,
            headers={"X-Rate-Limit-Remaining": "12", "X-Rate-Limit-Limit": "10000"},
        ),
    ), caplog.at_level("WARNING", logger="app.lms.blackboard"):
        connector.get_roster("_course_1")

    assert any("quota is low" in r.message.lower() for r in caplog.records)


def test_a_healthy_quota_does_not_warn(caplog):
    """The warning must be a signal, not noise — a healthy quota logs at debug."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response(
            {"results": []}, status_code=200,
            headers={"X-Rate-Limit-Remaining": "9500"},
        ),
    ), caplog.at_level("WARNING", logger="app.lms.blackboard"):
        connector.get_roster("_course_1")

    assert not any("quota is low" in r.message.lower() for r in caplog.records)


def test_a_response_without_quota_headers_is_not_an_error():
    """Blackboard only sends the rate-limit headers on some responses. Their
    absence must be silent, not an AttributeError in the middle of a launch."""
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=_rate_limit_settings()), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda path, **kw: _Response({"results": []}, status_code=200),
    ):
        assert connector.get_roster("_course_1") == []
