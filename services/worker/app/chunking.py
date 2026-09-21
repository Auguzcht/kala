"""Chunking for the worker's ingest walk.

DELIBERATE DUPLICATE of services/api/app/ai/chunking.py, same pattern and the
same reason as app/embed.py and app/tagger.py: the worker Dockerfile only
`COPY app ./app` and cannot import services/api at build time, and the two are
built and deployed as separate images. Moving the shared modules into
packages/ would mean changing both Dockerfiles — an infra-shaped change the
root CLAUDE.md says not to make unasked.

GREP DISCIPLINE. If the api's chunk_text changes its defaults, its overlap
handling, or its boundary logic, change it here too. The two MUST produce
identical chunk boundaries or a course ingested by the worker and one ingested
by the api's /content/upload path would embed different slices of the same
text, and retrieval quality would differ by which door the content came in.
Grep both trees for `chunk_text` before editing either.

WHY THIS MATTERS MORE THAN IT LOOKS. The scaffold stored each content item's
whole body as ONE chunk. That is not a neutral stub: a 4000-char module page
becomes a single embedding, so retrieval can only ever return "this entire
page" as a hit — the same coarse-grain problem the api side already solved.
Worse, it would have been invisible, because the drain would succeed and the
bank reset would then regenerate questions off bad chunks and bake the damage
in. Hence: real chunking before the first live drain, not after.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

# Chunk geometry. Copied from the api's chunking.py — keep in sync.
MAX_CHUNK_CHARS = 4000
CHUNK_OVERLAP = 200

# Which file types the walk will extract text from. Mirrors
# services/api/app/ai/documents.py's ALLOWED_MIME_TYPES.
ALLOWED_MIME_TYPES = {"text/plain", "text/markdown", "application/pdf"}

# Browsers/Blackboard report a generic content-type for some files, so the
# extension is consulted as a fallback before rejecting. Mirrors the api.
GENERIC_MIME_TYPES = {"", "application/octet-stream", "text/plain"}
EXTENSION_MIME_FALLBACK = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks. Duplicate of the api's chunk_text —
    identical boundaries, so retrieval behaves the same whichever path stored
    the content."""
    if not text:
        return []
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def strip_pii(text: str) -> str:
    """De-identify before anything is stored or later sent to a model.

    Duplicate of the api's strip_pii (app/ai/deidentify.py) WITHOUT its
    safe_context companion — that one needs CurrentUser from app.deps, which
    the worker has no notion of and the ingest path never uses. Hard rule from
    the root CLAUDE.md: no raw PII on the way to a model.

    Note this runs at STORE time on the api side, and the walk must do the same
    or a name in a course page would sit unstripped in content_items until
    something else cleaned it. In practice LMS course content is instructor
    prose rather than student data, but the rule is unconditional.
    """
    cleaned = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text or "")
    return re.sub(
        r"\b(?:姓名|name)\s*:\s*[^,;\n]+", "[name]", cleaned, flags=re.IGNORECASE,
    )


def resolve_mime_type(filename: str, declared: str | None) -> str:
    """The MIME type to treat a file as, or raise ValueError if unsupported.
    Mirrors the api's documents.resolve_mime_type."""
    mime = declared or ""
    if mime in GENERIC_MIME_TYPES:
        ext = Path(filename or "").suffix.lower()
        mime = EXTENSION_MIME_FALLBACK.get(ext, mime or "application/octet-stream")
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"unsupported file type: {mime}. Allowed: .txt, .md, .pdf")
    return mime


def extract_text(content: bytes, mime_type: str) -> str:
    """Best-effort text extraction. Raises on anything that fails to parse —
    the caller decides whether that is fatal or degraded. Mirrors the api's
    documents.extract_text; pypdf is imported lazily so the txt/md path needs
    no PDF library."""
    if mime_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content.decode("utf-8", errors="replace")
