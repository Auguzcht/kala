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
import html

from app.lms.blackboard import (
    BlackboardConnector, BlackboardRateLimitedError, _attachment_links, _to_plain_text,
)


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


class _RawResponse:
    """A response whose .content is bytes (an attachment download)."""

    def __init__(self, content: bytes, *, status_code: int = 200):
        self.content = content
        self.status_code = status_code
        self.headers = {}
        self.request = httpx.Request("GET", "https://learn.example/download")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(str(self.status_code), request=self.request, response=self)


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
        items, _stats = connector.get_content("_course_1")

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
        items, _stats = connector.get_content("_course_1")

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
        items, _stats = connector.get_content("_course_1")

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
        items, _stats = connector.get_content("_course_1")
        items = {i["lms_content_id"]: i for i in items}

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


# ---- attachment extraction (Lead B) ---------------------------------------
#
# The professor's AWS PDFs are embedded in Ultra document bodies as anchors
# carrying a data-bbfile JSON blob. Verified live 2026-09-19: the sibling href
# is self-authenticating (a plain GET follows a 302 to the bytes) while
# resourceUrl, a DIFFERENT signed URL in the same blob, 404s.
#
# The tests below pin the three things that cost real probe time:
#   1. attribute order is NOT stable (data-bbfile before or after href)
#   2. resourceUrl must never be used
#   3. a document with no data-bbfile must fall through to a normal item


def _anchor(href: str, blob: dict, *, blob_first: bool = False, text: str = "") -> str:
    import json as _json
    esc = html.escape(_json.dumps(blob))
    a = f'href="{href}"'
    b = f'data-bbfile="{esc}"'
    attrs = f"{b} {a}" if blob_first else f"{a} {b}"
    return f"<div><p><a {attrs}>{text}</a></p></div>"


def test_attachment_links_extracts_href_and_metadata():
    body = _anchor(
        "https://bb.example/bbcswebdav/xid-1?VxJw3wfC56=1789817965",
        {"mimeType": "application/pdf", "fileName": "Guide.pdf", "fileSize": 819568},
    )
    links = _attachment_links(body)
    assert len(links) == 1
    assert links[0]["href"] == "https://bb.example/bbcswebdav/xid-1?VxJw3wfC56=1789817965"
    assert links[0]["mime_type"] == "application/pdf"
    assert links[0]["file_name"] == "Guide.pdf"


def test_attachment_links_are_order_independent():
    """The live course had anchors with data-bbfile BEFORE href and anchors with
    no inner text at all. An early probe regex assumed href-first and silently
    missed most of the PDFs, so this is pinned rather than assumed."""
    blob = {"mimeType": "application/pdf", "fileName": "Module_01.pdf"}
    href = "https://bb.example/bbcswebdav/xid-2"
    for blob_first in (True, False):
        links = _attachment_links(_anchor(href, blob, blob_first=blob_first))
        assert len(links) == 1, f"missed the anchor (blob_first={blob_first})"
        assert links[0]["href"] == href


def test_attachment_links_skips_an_anchor_with_no_href():
    """Metadata without a fetchable URL is not an attachment we can use."""
    import json as _json
    body = f'<a data-bbfile="{html.escape(_json.dumps({"mimeType": "application/pdf"}))}"></a>'
    assert _attachment_links(body) == []


def test_attachment_links_survives_malformed_json():
    """One broken anchor must not lose the rest of the body's attachments."""
    good_href = "https://bb.example/bbcswebdav/xid-good"
    good = _anchor(good_href, {"mimeType": "application/pdf", "fileName": "ok.pdf"})
    body = '<a href="https://x/y" data-bbfile="{not json}"></a>' + good
    links = _attachment_links(body)
    assert len(links) == 1
    assert links[0]["href"] == good_href


def test_attachment_links_uses_href_not_resourceurl():
    """Both URLs are in the blob. resourceUrl is the inline-render variant and
    returns 404 on this instance; using it would look like a successful
    extraction and fail at fetch time."""
    body = _anchor(
        "https://bb.example/bbcswebdav/pid-622-dt-content-rid-5560/xid-5560",
        {
            "mimeType": "application/pdf", "fileName": "Guide.pdf",
            "resourceUrl": "https://bb.example/bbcswebdav/pid-622-dt-content-rid-46141487/xid-46141487",
        },
    )
    links = _attachment_links(body)
    assert "rid-5560" in links[0]["href"]
    assert "46141487" not in links[0]["href"]


def test_attachment_links_finds_every_anchor_in_one_body():
    """A real body held a PDF plus several screenshots; all must be seen so the
    caller can apply the MIME filter itself."""
    body = (
        _anchor("https://bb.example/a", {"mimeType": "application/pdf", "fileName": "a.pdf"})
        + _anchor("https://bb.example/b", {"mimeType": "image/png", "fileName": "b.png"})
        + _anchor("https://bb.example/c", {"mimeType": "image/jpeg", "fileName": "c.jpg"})
    )
    links = _attachment_links(body)
    assert [l["mime_type"] for l in links] == ["application/pdf", "image/png", "image/jpeg"]


def test_attachment_links_returns_empty_for_a_body_with_none():
    assert _attachment_links("<div><p>Just prose, no files.</p></div>") == []
    assert _attachment_links("") == []


def test_attachment_links_prefers_filename_over_linkname():
    body = _anchor("https://bb.example/a", {
        "mimeType": "application/pdf", "fileName": "real.pdf", "linkName": "Read me",
    })
    assert _attachment_links(body)[0]["file_name"] == "real.pdf"
    # ...and falls back to linkName when fileName is absent (some anchors).
    body2 = _anchor("https://bb.example/b", {
        "mimeType": "application/pdf", "linkName": "Read me",
    })
    assert _attachment_links(body2)[0]["file_name"] == "Read me"


# ---- the gate: include_attachments defaults to the cheap path --------------


def test_get_content_does_not_fetch_attachments_by_default():
    """Three callers share this method: the debug preview route, propose_skills,
    and _seed_course_skills — the last of which runs on every instructor launch
    under a 'never blocks the 302' contract. Default False must keep them all on
    the metadata-only path."""
    body = _anchor("https://bb.example/pdf", {"mimeType": "application/pdf", "fileName": "x.pdf"})
    root = [{"id": "_1_1", "title": "Page", "body": body,
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    fetched = []

    def spy_get(path, **kw):
        if "bbcswebdav" in str(path):
            fetched.append(path)
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=spy_get
    ):
        items, stats = connector.get_content("_course_1")

    assert fetched == [], "the default path must not download any attachment"
    assert stats["fetched"] == 0
    assert items[0]["attachments"] == []


def test_get_content_fetches_and_extracts_when_asked():
    """The ingest path opts in and gets text back, capped by max_attachments."""
    body = _anchor("https://bb.example/pdf-a", {"mimeType": "application/pdf", "fileName": "a.pdf"})
    root = [{"id": "_1_1", "title": "Page", "body": body,
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    def fake_get(path, **kw):
        if "bbcswebdav" in str(path) or "bb.example" in str(path):
            return _RawResponse(b"%PDF-1.7 fake")
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ), patch("app.ai.documents.extract_text", return_value="Extracted PDF body text."):
        items, stats = connector.get_content("_course_1", include_attachments=True)

    assert stats["fetched"] == 1
    assert stats["remaining"] == 0
    atts = items[0]["attachments"]
    assert len(atts) == 1
    assert atts[0]["text"] == "Extracted PDF body text."
    assert atts[0]["chunks"] == ["Extracted PDF body text."]


def test_get_content_skips_non_document_mime_types():
    """Screenshots share the same markup. Fetching them wastes a cap slot and
    extracts to nothing."""
    body = (
        _anchor("https://bb.example/a.png", {"mimeType": "image/png", "fileName": "a.png"})
        + _anchor("https://bb.example/b.jpg", {"mimeType": "image/jpeg", "fileName": "b.jpg"})
    )
    root = [{"id": "_1_1", "title": "Page", "body": body,
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    def fake_get(path, **kw):
        if "bbcswebdav" in str(path) or str(path).endswith((".png", ".jpg")):
            raise AssertionError("must not fetch a non-document attachment")
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ):
        items, stats = connector.get_content("_course_1", include_attachments=True)

    assert stats["fetched"] == 0
    assert stats["skipped_unsupported"] == 2
    assert items[0]["attachments"] == []


def test_get_content_caps_fetches_and_reports_what_is_left():
    """The cap is what keeps this inside the Lambda 30s wall. `remaining` is how
    the caller learns to call again — it must count what the CAP held back."""
    hrefs = [f"https://bb.example/pdf-{i}" for i in range(5)]
    body = "".join(
        _anchor(h, {"mimeType": "application/pdf", "fileName": f"{i}.pdf"})
        for i, h in enumerate(hrefs)
    )
    root = [{"id": "_1_1", "title": "Page", "body": body,
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    seen = []

    def fake_get(path, **kw):
        if "pdf-" in str(path):
            seen.append(path)
            return _RawResponse(b"%PDF-1.7 x")
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ), patch("app.ai.documents.extract_text", return_value="text"):
        items, stats = connector.get_content(
            "_course_1", include_attachments=True, max_attachments=3,
        )

    assert len(seen) == 3, "must not exceed the cap"
    assert stats["fetched"] == 3
    assert stats["remaining"] == 2, "the caller needs this to know to call again"


def test_one_failed_attachment_does_not_lose_the_others():
    """Same per-item isolation the subtree walk already has. A dead link must
    not abort the course."""
    body = (
        _anchor("https://bb.example/dead", {"mimeType": "application/pdf", "fileName": "dead.pdf"})
        + _anchor("https://bb.example/live", {"mimeType": "application/pdf", "fileName": "live.pdf"})
    )
    root = [{"id": "_1_1", "title": "Page", "body": body,
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    def fake_get(path, **kw):
        if "dead" in str(path):
            raise httpx.ConnectError("gone")
        if "live" in str(path):
            return _RawResponse(b"%PDF-1.7 y")
        return _Response({"results": root})

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get", side_effect=fake_get
    ), patch("app.ai.documents.extract_text", return_value="live text"):
        items, stats = connector.get_content("_course_1", include_attachments=True)

    assert stats["fetched"] == 1
    assert stats["failed"] == 1
    assert len(items[0]["attachments"]) == 1
    assert items[0]["attachments"][0]["text"] == "live text"
    # A FAILED fetch is NOT counted as remaining, or the number would never
    # reach 0 and "call until remaining is 0" would be a lie.
    assert stats["remaining"] == 0


def test_document_item_with_no_data_bbfile_still_yields_a_normal_item():
    """The fall-through: most items have plain prose and no attachments. They
    must come through untouched, with an empty attachments list."""
    root = [{"id": "_1_1", "title": "Vision", "body": "<p>Excellence and relevance.</p>",
             "contentHandler": {"id": "resource/x-bb-document"}}]
    settings = Settings(LMS_REST_BASE_URL="https://learn.example/learn/api/public/v1",
                        LMS_VERIFY_TLS=False)
    connector = BlackboardConnector()
    connector._headers = lambda: {"Authorization": "Bearer test"}

    with patch("app.lms.blackboard.get_settings", return_value=settings), patch(
        "app.lms.blackboard.httpx.get",
        side_effect=lambda p, **kw: _Response({"results": root}),
    ):
        items, stats = connector.get_content("_course_1", include_attachments=True)

    assert items[0]["body_or_description"] == "Excellence and relevance."
    assert items[0]["attachments"] == []
    assert stats["fetched"] == 0
