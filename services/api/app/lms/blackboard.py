"""Blackboard (Anthology) connector over the Learn REST API. Uses an OAuth 2
client-credentials token from the Learn token endpoint. Methods are partial;
fill in the response mapping against your instance's REST schema.

For roster and grade passback you may also use LTI NRPS and AGS from the launch
claims; both are valid. REST is the simpler data pipe for the pilot."""
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
from app.lms.base import LMSConnector

logger = logging.getLogger(__name__)

# Warn below this many remaining requests. Blackboard's quota is 10,000 for the
# window; a 500 floor leaves room to notice and stop hammering rather than
# discovering exhaustion when launches start failing. This is the cheap
# early-warning signal whose absence let a full-quota outage arrive unannounced.
_RATE_LIMIT_WARN_BELOW = 500


class BlackboardRateLimitedError(RuntimeError):
    """Blackboard answered 429. Carries the retry-after seconds when present.

    A distinct type, not a wrapped HTTPStatusError, because the correct
    response is different from every other transport failure: retrying
    immediately is GUARANTEED to fail again and costs another request against a
    quota already at zero. So callers must not treat this as retryable — they
    should fail once, cleanly, and say when to come back (see lti/routes.py).
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
    """Retry-After in seconds, or None.

    The header is specified as either delta-seconds or an HTTP-date, but the
    live Blackboard instance (verified against a real 429 on 2026-09-17) sends
    NEITHER of the bare forms — it sends `Retry-After: 20807s`, with a trailing
    unit letter. A plain int(float(...)) parse therefore fails on the exact
    response this function exists to read, silently downgrading a precise
    "retry after 20807 seconds" to a vague "when the window resets". Parse the
    digits and tolerate a trailing unit.

    An unparseable value still degrades to None rather than raising: a
    confusing header must not turn a rate-limit into a crash.
    """
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    # Strip a trailing unit if present ("s", "sec", "seconds"). Leading digits
    # are what matter; the live instance appends "s" and the spec does not.
    match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(raw))
    if not match:
        return None
    try:
        return int(float(match.group(1)))
    except ValueError:
        return None


def _check_rate_limit(resp: httpx.Response) -> None:
    """Raise BlackboardRateLimitedError on 429; warn when remaining is low.

    Called BEFORE raise_for_status so a 429 becomes the specific type above
    rather than a generic HTTPStatusError. On success this logs the remaining
    quota: the header is only present on some responses, so its absence is not
    an error, just nothing to report.
    """
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
            "Blackboard quota is low: %s requests remaining (limit %s) after %s",
            left, resp.headers.get("X-Rate-Limit-Limit", "?"), resp.request.url,
        )
    else:
        logger.debug(
            "Blackboard quota: %s remaining after %s", left, resp.request.url,
        )

# Blackboard's LTI test tool writes a literal placeholder into
# preferredDisplayName when the name form is left blank; treat it as
# missing and fall through to given/family (see get_roster).
_PLACEHOLDER_NAMES = {"givenname", "given name", "familyname", "family name", "test student"}


class _HTMLTextExtractor(HTMLParser):
    """Strip tags from Blackboard's rich-text bodies, keeping the words.

    Blackboard returns page bodies as BBML/HTML — the live course's Vision /
    Mission page arrives as ~1500 chars of `<div data-bbid=...><span style=...>`
    wrapper markup around a few sentences of real text. Feeding that raw to the
    chunker stores markup as "course content", and feeding it to the model as an
    "excerpt" wastes the context window on attributes. Standard library only:
    this is a small, well-defined job and does not justify a parser dependency.

    Block-level tags become newlines so words from adjacent paragraphs do not
    run together into a single nonsense sentence.
    """

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
        # Collapse the run of blank lines the block tags produce, and normalise
        # the non-breaking spaces Blackboard emits into ordinary spaces.
        joined = joined.replace("\xa0", " ")
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n\s*\n\s*\n+", "\n\n", joined)
        return joined.strip()


# Attachment anchors in an Ultra document body look like:
#   <a href="...bbcswebdav/pid-N-dt-content-rid-M/xid-M?Kq3...&VxJw..."
#      data-bbtype="attachment"
#      data-bbfile="{&quot;fileName&quot;:&quot;...pdf&quot;,&quot;fileSize&quot;:819568,
#                    &quot;mimeType&quot;:&quot;application/pdf&quot;,&quot;resourceUrl&quot;:&quot;...&quot;}">
#      Link text</a>
#
# `data-bbfile` is HTML-escaped JSON. The sibling `href` is the real file and
# is SELF-AUTHENTICATING — verified live 2026-09-19: a plain unauthenticated
# GET follows a 302 to the actual bytes, no bearer token and no JSESSIONID
# required. `resourceUrl` also appears in the JSON but is a DIFFERENT signed
# URL (the inline-render variant) and returns 404; always use the href.
#
# ATTRIBUTE ORDER IS NOT STABLE. Some anchors put data-bbfile before href, some
# after, and some have no inner text at all. An early probe regex assumed
# `href` first and silently missed most of the course's PDFs — so this parses
# each whole anchor tag and pulls the attributes out of it, rather than
# pattern-matching a fixed order.
_ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
_BBFILE_RE = re.compile(r'data-bbfile="(.*?)"', re.DOTALL)
_HREF_RE = re.compile(r'href="([^"]+)"')


def _attachment_links(raw_body: str) -> list[dict]:
    """Attachments embedded in a document body, parsed from the anchors.

    Returns one dict per anchor that carries a `data-bbfile` JSON blob AND a
    usable href: {mime_type, file_name, file_size, href}. Anchors without a
    href are skipped — they are metadata for something the body renders
    inline, not a fetchable file.

    Pure parsing, NO network. The caller decides which of these to download;
    this is deliberately cheap so it can run inside `get_content` for every
    caller without turning a tree-walk into a download.
    """
    links: list[dict] = []
    for tag in _ANCHOR_RE.findall(raw_body or ""):
        blob = _BBFILE_RE.search(tag)
        if not blob:
            continue
        href = _HREF_RE.search(tag)
        if not href:
            continue
        try:
            meta = json.loads(_html.unescape(blob.group(1)))
        except (ValueError, TypeError):
            # Malformed JSON in one anchor must not lose the whole body's
            # attachments — skip it, same spirit as the per-subtree catch in
            # get_content.
            continue
        if not isinstance(meta, dict):
            continue
        links.append({
            "mime_type": meta.get("mimeType"),
            "file_name": meta.get("fileName") or meta.get("linkName"),
            "file_size": meta.get("fileSize"),
            "href": _html.unescape(href.group(1)),
        })
    return links


def fetch_attachment(href: str) -> bytes:
    """Download an attachment's bytes from its body href.

    Deliberately contains NO Authorization header: the bbcswebdav URL carries
    its own short-lived signature (the `VxJw3wfC56` query param is a unix
    timestamp), and sending a bearer token alongside it adds nothing while
    risking the host rejecting a request it did not expect to be authenticated.

    The signature EXPIRES, so an href must be fetched close to when it was
    read out of a body. Caching one for a later run guarantees a 404.
    """
    s = get_settings()
    resp = httpx.get(href, follow_redirects=True, verify=s.lms_verify_tls, timeout=30.0)
    resp.raise_for_status()
    return resp.content


def _to_plain_text(raw: str) -> str:
    """HTML/BBML body → plain text. Ordinary prose passes through with entity
    decoding and whitespace normalisation, so this is safe to call
    unconditionally. Bodies can contain entities without any tags at all
    ("Excellence&nbsp;and&nbsp;Relevance"), so the no-tag path must still run
    through the same extraction rather than short-circuiting."""
    if not raw:
        return ""
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        # A malformed body must not fail an ingest run; fall back to a crude
        # tag strip so the words still survive.
        return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
    return parser.text()


class BlackboardConnector(LMSConnector):
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _get_token(self) -> str:
        s = get_settings()
        if self._token and time.time() < self._expires_at - 30:
            return self._token
        # Learn REST uses application key/secret via client_credentials.
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
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/externalId:{quote(external_id, safe='')}",
            headers=self._headers(),
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()["id"]

    def get_roster(self, course_ref: str) -> list[dict]:
        """Full course roster, following pagination to exhaustion.

        This used to matter only for completeness — an unpaginated pull
        just meant "you might be missing some students" on a display. Now
        that a full pull also drives deletion (lti/routes.py._sync_roster
        removes any Kala enrollment not present in this list), an
        incomplete page is worse than incomplete: it would report a fully
        enrolled student as absent and reconciliation would remove them.

        Follows Learn REST's `paging.nextPage` continuation link, which is
        typically returned as a path relative to the API root once a
        response exceeds the default page size. VERIFY the exact key name
        and whether your instance returns a relative path or an absolute
        URL before relying on this in production — this loop handles both,
        but it has not been run against a live paginated response.
        """
        s = get_settings()
        params = {
            "expand": "users",
            "fields": "userId,courseRoleId,user.id,user.name,user.contact.email",
        }
        results: list[dict] = []
        path = f"{s.lms_rest_base_url}/courses/{course_ref}/users"

        while path:
            resp = httpx.get(
                path,
                headers=self._headers(),
                params=params if "?" not in path else None,
                verify=s.lms_verify_tls,
                timeout=15.0,
            )
            _check_rate_limit(resp)
            resp.raise_for_status()
            body = resp.json()
            results.extend(body.get("results", []))

            next_page = (body.get("paging") or {}).get("nextPage")
            if not next_page:
                break
            # nextPage may already be a full URL, or a path relative to the
            # API host — handle both rather than assuming one.
            path = next_page if next_page.startswith("http") else f"{s.lms_rest_base_url.rstrip('/')}{next_page}"
            params = None  # the continuation link already encodes the query

        roster = []
        for membership in results:
            user = membership.get("user", {})
            name = user.get("name", {})
            # preferredDisplayName must not shadow real names: Blackboard
            # returns the literal placeholder "GivenName" as
            # preferredDisplayName for accounts the LTI test tool created
            # without filling the name form, and it is truthy, so it would
            # win over given/family here and the roster sync would write
            # "GivenName" into user_profiles on every launch — which is
            # exactly why the roster showed "anon-*" for accounts whose
            # real BB names (Alfred Nodado, Hanna Sato) were sitting in
            # given/family all along. Same placeholder guard as
            # cohort.load_identities; this fixes it at the source so the
            # sync persists real names, durable across reconciles.
            preferred = (name.get("preferredDisplayName") or "").strip()
            display_name = (
                preferred
                if preferred and preferred.lower() not in _PLACEHOLDER_NAMES
                else " ".join(
                    part for part in (name.get("given"), name.get("family")) if part
                )
            )
            roster.append({
                "lms_user_id": membership["userId"],
                "role": membership.get("courseRoleId"),
                "name": display_name,
                "email": user.get("contact", {}).get("email"),
            })
        return roster

    def get_content(self, course_ref: str, *, include_attachments: bool = False,
                    max_attachments: int = 3) -> tuple[list[dict], dict]:
        """The course's content tree, flattened, with each item's text body.

        Returns (items, attachment_stats). The stats dict reports what the PDF
        fetch actually did this call — `fetched`, `skipped_unsupported`,
        `failed`, `capped`, `remaining` — so "call /ingest until remaining is
        0" is an observable fact in the response rather than tribal knowledge
        in a comment.

        `include_attachments=False` (the DEFAULT) returns the cheap
        metadata-only walk. Only the ingest path opts in:

          - GET /courses/{id}/content (the debug preview) asks for a quick look
            at the tree; downloading and parsing every PDF there would be
            surprising and slow.
          - propose_skills and _seed_course_skills read bodies to propose
            skills from. _seed_course_skills in particular runs on EVERY
            instructor launch under an explicit "never blocks the 302"
            contract — the exact flow that burned this instance's 10,000
            request quota on 2026-09-17. It must stay cheap.

        Defaulting to False is the safe direction: a future caller gets the
        cheap path unless it deliberately asks for the expensive one.

        TWO THINGS THIS GETS WRONG ON PURPOSE, both named here rather than
        discovered later:

        1. THE CAP IS NOT A RESUMPTION CURSOR. At most `max_attachments` PDFs
           are downloaded per call, so ONE call will not ingest every PDF in a
           course. Completion means calling until `attachment_stats["remaining"]`
           is 0. The cap exists because fetch is network-bound (~2s per file
           measured, 16s for this course's 8 PDFs) and the Lambda wall is 30s.
           An uncapped walk is exactly the failure mode that killed the old
           tagging loop.

        2. A PERMANENTLY BROKEN HREF OCCUPIES A CAP SLOT FOREVER. If a fetch
           raises (expired signature, malformed URL, 404), nothing is stored,
           so the existing_refs dedupe downstream never marks it done and it
           will be retried — and consume one of the 3 slots — on every future
           call. That is an accepted limitation of this first pass, not an
           oversight: the observed failure mode is a small number of stale
           external-host links, and the alternative (a per-attachment failure
           ledger) is a new table for a problem that does not yet justify one.
           If a course ever shows a permanently stuck `remaining`, this is why.
        """
        s = get_settings()
        headers = self._headers()
        visited: set[str] = set()

        def fetch_children(parent_id: str | None = None) -> list[dict]:
            path = f"{s.lms_rest_base_url}/courses/{course_ref}/contents"
            if parent_id:
                path += f"/{parent_id}/children"
            resp = httpx.get(
                path,
                headers=headers,
                verify=s.lms_verify_tls,
                timeout=15.0,
            )
            _check_rate_limit(resp)
            resp.raise_for_status()
            return resp.json().get("results", [])

        # Blackboard's container handlers — the content-type ids that mean
        # "this node holds other nodes". Matching on handler id keeps this
        # independent of the display title ("Module 2|Building Blocks").
        container_markers = ("resource/x-bb-folder", "resource/x-bb-lesson",
                             "resource/x-bb-learning-module")

        # What the attachment pass did this call. Mutated by flatten().
        stats = {
            "fetched": 0,
            "skipped_unsupported": 0,
            "failed": 0,
            "capped": 0,
            "remaining": 0,
            "chunks": 0,
        }

        # Imported here, not at module scope: services/api's documents module
        # pulls in pypdf lazily, and the connector is imported by the worker's
        # LTI path where PDF parsing is irrelevant. Keeps the import graph
        # honest about what the connector itself needs.
        from app.ai.documents import ALLOWED_MIME_TYPES, extract_text
        from app.ai.chunking import chunk_text as _chunk_text

        def attachments_for(item: dict) -> list[dict]:
            """The item's PDF (and other allowed-type) attachments, fetched and
            turned into text, bounded by the per-call cap and the MIME filter."""
            if not include_attachments:
                return []
            out: list[dict] = []
            for link in _attachment_links(item.get("body") or ""):
                mime = (link.get("mime_type") or "").strip()
                if mime not in ALLOWED_MIME_TYPES:
                    # Screenshots and external-host links live in the same
                    # markup; only parseable document types are worth a fetch.
                    stats["skipped_unsupported"] += 1
                    continue
                if stats["fetched"] >= max_attachments:
                    # Over the per-call cap. Counted, NOT fetched, and reported
                    # to the caller so it knows to call again.
                    stats["capped"] += 1
                    continue
                try:
                    data = fetch_attachment(link["href"])
                    text = extract_text(data, mime)
                except Exception as exc:  # noqa: BLE001 — one bad file must not kill the walk
                    # Same contract as the per-subtree catch below: one
                    # unreadable attachment is skipped, the rest of the course
                    # is still worth storing. Note this leaves the href
                    # un-stored, so it will be retried next call — see point 2
                    # in the docstring.
                    logger.warning(
                        "attachment fetch failed for %s (%s): %s",
                        item.get("title"), link.get("file_name"), exc,
                    )
                    stats["failed"] += 1
                    continue
                stats["fetched"] += 1
                out.append({
                    "file_name": link.get("file_name") or item.get("title") or "attachment",
                    "text": text,
                    "chunks": _chunk_text(text),
                })
                stats["chunks"] += len(out[-1]["chunks"])
            return out

        def flatten(items: list[dict]) -> list[dict]:
            content = []
            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in visited:
                    continue
                visited.add(item_id)

                handler = item.get("contentHandler") or {}
                handler_id = handler.get("id") or ""
                body = _to_plain_text(item.get("body") or "")
                description = _to_plain_text(item.get("description") or "")
                content.append({
                    "lms_content_id": item_id,
                    "title": item.get("title") or "Untitled",
                    # body first (real page text), description only as a
                    # fallback. Both are now stripped to plain text.
                    "body_or_description": body or description,
                    "content_type": handler_id,
                    "parent_id": item.get("parentId"),
                    # Extracted attachment text, or [] on the cheap path. Each
                    # entry carries its own chunks so the ingest route can store
                    # them as separate content_items under the same parent —
                    # a PDF is content in its own right, not a suffix on the
                    # page that linked it.
                    "attachments": attachments_for(item),
                })

                is_container = bool(item.get("hasChildren")) or any(
                    marker in handler_id for marker in container_markers
                )
                if is_container:
                    try:
                        content.extend(flatten(fetch_children(item_id)))
                    except httpx.HTTPError:
                        # One unreadable subtree must not abort the whole
                        # ingest — the rest of the course is still worth
                        # storing, and a silent partial tree is what hid this
                        # bug in the first place, so the caller counts what it
                        # got (see ingest_course's stored/embedded totals).
                        continue
            return content

        items = flatten(fetch_children())
        # `remaining` is what the caller needs to decide whether to call again:
        # everything it did not fetch because of the cap. Failures are NOT
        # counted here — a failed fetch is retried next call by construction,
        # but counting failed hrefs as "remaining" would make the number never
        # reach 0 and turn the completion signal into a lie.
        stats["remaining"] = stats["capped"]
        return items, stats

    def get_assessments(self, course_ref: str) -> list[dict]:
        s = get_settings()
        resp = httpx.get(
            f"{s.lms_rest_base_url}/courses/{course_ref}/gradebook/columns",
            headers=self._headers(),
            params={
                "fields": "id,name,displayName,score.possible,grading.type",
            },
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()

        return [{
            "lms_column_id": column["id"],
            "name": column.get("name") or column.get("displayName") or "Untitled",
            "points_possible": (column.get("score") or {}).get("possible"),
            "grading_type": (column.get("grading") or {}).get("type"),
        } for column in resp.json().get("results", [])]

    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None:
        s = get_settings()
        resp = httpx.patch(
            f"{s.lms_rest_base_url}/courses/{course_ref}/gradebook/columns/{column_id}/users/{user_ref}",
            headers=self._headers(),
            json={"score": score},
            verify=s.lms_verify_tls,
            timeout=15.0,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
