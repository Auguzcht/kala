"""Worker-side Blackboard connector — a DELIBERATE, TRIMMED duplicate of
services/api/app/lms/blackboard.py, carrying only what the incremental ingest
walk needs. Same reason app/embed.py and app/tagger.py are duplicates: the
worker Dockerfile only `COPY app ./app` and cannot import services/api. Making
them share code means moving modules into packages/ and changing both
Dockerfiles — an infra-shaped change the root CLAUDE.md says not to make
unasked. So this is a duplicate by design.

WHAT IS AND ISN'T HERE. The api connector does the whole recursive walk in one
call (get_content). The worker does NOT — it expands ONE bounded frontier slice
per invocation and checkpoints between them (see app/jobs/ingest_walk.py). So
this file exposes the primitives that walk needs:

  - _get_token / _headers            OAuth client-credentials, same as api
  - _check_rate_limit / _retry_after the 429 + quota-warning machinery, copied
                                     VERBATIM — the walk must respect the same
                                     limits that this whole effort exists to fix
  - fetch_children(course_ref, id)   one level of the tree, one REST call
  - flatten_item(raw)                raw Blackboard item -> the stored shape,
                                     including plain-text body extraction
  - is_container(raw)                does this node hold children (folder walk)
  - extract_pdf_attachments(raw)     Lead B: pull data-bbfile href(s) from a
                                     body before markup is stripped
  - download(href)                   fetch a signed bbcswebdav href (no OAuth)

GREP DISCIPLINE. Every symbol here mirrors the api. If the api changes the
Retry-After parse, the container marker set, the BBML extractor, or the
data-bbfile parse, change it here too. Grep both trees for the symbol first.

STATUS: SCAFFOLD. The rate-limit block and the BBML extractor are copied to
match the api. The fetch_children / flatten_item / extract_pdf_attachments /
download bodies are written to the api's verified behavior but have NOT been
run against the live instance from the worker image yet — that's DeepSeek's
first build-time step (see the brief). Marked with TODO(verify-live).
"""
from __future__ import annotations

import html as _html
import json
import logging
import re
import time
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger("kala.worker")

_RATE_LIMIT_WARN_BELOW = 500


class BlackboardRateLimitedError(RuntimeError):
    """Blackboard answered 429. Carries retry-after seconds when present.

    Distinct type, copied from the api connector: retrying immediately is
    guaranteed to fail again and costs another request against an exhausted
    quota. The walk job must catch this, checkpoint the frontier it has, and
    stop cleanly — NOT loop.
    """

    def __init__(self, *, retry_after: int | None, path: str):
        self.retry_after = retry_after
        self.path = path
        detail = (
            f"retry after roughly {retry_after} seconds"
            if retry_after is not None
            else "retry after the current quota window resets"
        )
        super().__init__(f"Blackboard rate limited {path}; {detail}")


def _retry_after_seconds(resp: httpx.Response) -> int | None:
    """Retry-After in seconds, tolerating the live instance's trailing-unit
    form ("20807s"). Copied verbatim from the api connector — keep in sync."""
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(raw))
    if not match:
        return None
    try:
        return int(float(match.group(1)))
    except ValueError:
        return None


def _check_rate_limit(resp: httpx.Response) -> None:
    """Raise BlackboardRateLimitedError on 429; warn when remaining is low.
    Copied verbatim from the api connector — keep in sync."""
    if resp.status_code == 429:
        raise BlackboardRateLimitedError(
            retry_after=_retry_after_seconds(resp), path=str(resp.request.url),
        )
    remaining = resp.headers.get("X-Rate-Limit-Remaining")
    if remaining is None:
        return
    try:
        left = int(remaining)
    except (TypeError, ValueError):
        return
    if left < _RATE_LIMIT_WARN_BELOW:
        logger.warning(
            "Blackboard quota is low: %s remaining (limit %s) after %s",
            left, resp.headers.get("X-Rate-Limit-Limit", "?"), resp.request.url,
        )


class _HTMLTextExtractor(HTMLParser):
    """Strip BBML/HTML to plain text. Copied from the api connector; keep in
    sync. Block tags become newlines so adjacent paragraphs don't run together."""

    _BLOCK = {
        "p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3",
        "h4", "h5", "h6", "table", "section", "article", "blockquote",
    }
    _SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        joined = "".join(self._parts)
        joined = joined.replace("\xa0", " ")
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n\s*\n\s*\n+", "\n\n", joined)
        return joined.strip()


def _to_plain_text(raw: str) -> str:
    if not raw:
        return ""
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
    return parser.text()


# Container handlers — the content-type ids that mean "holds other nodes".
# Copied from the api connector's get_content; keep in sync.
_CONTAINER_MARKERS = (
    "resource/x-bb-folder", "resource/x-bb-lesson", "resource/x-bb-learning-module",
)

# Lead B: any anchor tag, order-independent (some anchors put data-bbfile before
# href — DeepSeek's probe found this the hard way). Parse the whole tag, then
# pull href and data-bbfile out of it separately.
_ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.I | re.S)
_HREF_RE = re.compile(r'href="([^"]+)"', re.I)
_BBFILE_RE = re.compile(r'data-bbfile="(.*?)"', re.I | re.S)

# Which attachment mime types to fetch. Mirrors documents.ALLOWED_MIME_TYPES on
# the api side — start with PDF. Keep in sync with that set.
_FETCHABLE_MIME_TYPES = {"application/pdf"}


class WorkerBlackboardConnector:
    """Frontier-walk primitives. NOT a full get_content — the walk job composes
    fetch_children + flatten_item + is_container itself, checkpointing between
    levels (app/jobs/ingest_walk.py)."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _get_token(self) -> str:
        s = get_settings()
        if self._token and time.time() < self._expires_at - 30:
            return self._token
        resp = httpx.post(
            s.lti_auth_token_url,
            data={"grant_type": "client_credentials"},
            auth=(s.lms_rest_client_id, s.lms_rest_client_secret),
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def resolve_course_ref(self, external_id: str) -> str:
        """Kept so the worker can resolve a course by external id if a job ever
        stores that instead of the internal ref. TODO(verify-live)."""
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/externalId:{quote(external_id, safe='')}",
            headers=self._headers(), verify=s.lms_verify_tls, timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()["id"]

    def fetch_children(self, course_ref: str, parent_id: str | None = None) -> list[dict]:
        """One level of the tree = one REST call. The walk job calls this once
        per frontier entry it pops, then checkpoints. TODO(verify-live)."""
        s = get_settings()
        path = f"{s.lms_rest_base_url}/courses/{course_ref}/contents"
        if parent_id:
            path += f"/{parent_id}/children"
        resp = httpx.get(
            path, headers=self._headers(), verify=s.lms_verify_tls, timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
        return resp.json().get("results", [])

    @staticmethod
    def is_container(raw: dict) -> bool:
        handler_id = (raw.get("contentHandler") or {}).get("id") or ""
        return bool(raw.get("hasChildren")) or any(
            marker in handler_id for marker in _CONTAINER_MARKERS
        )

    @staticmethod
    def flatten_item(raw: dict) -> dict:
        """Raw Blackboard item -> stored shape. Same field mapping as the api
        connector's flatten(), including body-first plain-text extraction.
        Keep in sync with services/api get_content()."""
        handler = raw.get("contentHandler") or {}
        body = _to_plain_text(raw.get("body") or "")
        description = _to_plain_text(raw.get("description") or "")
        return {
            "lms_content_id": raw.get("id"),
            "title": raw.get("title") or "Untitled",
            "body_or_description": body or description,
            "content_type": handler.get("id") or "",
            "parent_id": raw.get("parentId"),
        }

    @staticmethod
    def extract_pdf_attachments(raw: dict) -> list[dict]:
        """Lead B. Pull fetchable attachments out of a body BEFORE markup is
        stripped. Returns [{href, mimeType, fileName, fileSize}]. Parses the
        whole anchor tag then reads href + data-bbfile independently, so
        attribute order does not matter. Use href, NOT resourceUrl (the latter
        404s). Keep in sync with the api-side Lead B extraction. TODO(verify-live)."""
        body = raw.get("body") or ""
        if not body:
            return []
        out: list[dict] = []
        for tag in _ANCHOR_RE.findall(body):
            bb = _BBFILE_RE.search(tag)
            if not bb:
                continue
            try:
                meta = json.loads(_html.unescape(bb.group(1)))
            except Exception:
                continue
            if meta.get("mimeType") not in _FETCHABLE_MIME_TYPES:
                continue
            href_match = _HREF_RE.search(tag)
            if not href_match:
                continue
            out.append({
                "href": _html.unescape(href_match.group(1)),
                "mimeType": meta.get("mimeType"),
                "fileName": meta.get("fileName") or meta.get("linkName"),
                "fileSize": meta.get("fileSize"),
            })
        return out

    def download(self, href: str) -> bytes:
        """Fetch a signed bbcswebdav href. Self-authenticating — no OAuth
        header — but SHORT-LIVED, so call this close to extraction, never from a
        stored href. Follows the 302 to the signed URL. TODO(verify-live).

        _check_rate_limit IS called here even though this host is not the REST
        API. Without it a 429 on a PDF download raised a plain
        HTTPStatusError, which _fetch_pdfs' `except Exception` swallows and
        continues past — so the ONE path that can quietly burn requests into
        an exhausted quota was also the one path the throttle logic could not
        see. With it, a 429 here becomes BlackboardRateLimitedError like every
        other call site, the walk checkpoints, and run() stops for the window.
        """
        s = get_settings()
        resp = httpx.get(href, follow_redirects=True, verify=s.lms_verify_tls, timeout=30.0)
        _check_rate_limit(resp)
        resp.raise_for_status()
        return resp.content
