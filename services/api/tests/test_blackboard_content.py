"""Tests for the Blackboard content extraction fixes.

Both bugs here were found by auditing why generated questions were meaningless
(not by a failing test): the connector stored HTML as if it were content, and
it only walked a fraction of the course tree. The narrow functions are tested
directly; the live tree shape is verified by the ingest diagnostic log, since
it depends on a real Blackboard instance this suite cannot reach.
"""
from unittest.mock import patch

from app.config import Settings
from app.lms.blackboard import BlackboardConnector, _to_plain_text


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
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

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
