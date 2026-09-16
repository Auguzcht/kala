"""Shared document handling: safe filenames, MIME allow-listing, and text
extraction for the file types Kala accepts.

Extracted from routers/tutor.py once a SECOND caller needed the same logic
(institution course-content uploads). Two copies of "which MIME types are
allowed" and "how do we pull text out of a PDF" is exactly the drift that
ends with a PDF that parses for one feature and 500s for another.

Nothing here is student-specific or storage-specific: it takes bytes and a
MIME type and returns text, or raises. The callers decide what to do with a
failure (tutor marks an attachment 'failed'; ingest skips the chunk).
"""
from __future__ import annotations

import io
from pathlib import Path

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

ALLOWED_MIME_TYPES = {"text/plain", "text/markdown", "application/pdf"}

# Browsers report an empty or generic content-type for some uploads, so the
# file extension is consulted as a fallback before rejecting.
GENERIC_MIME_TYPES = {"", "application/octet-stream", "text/plain"}
EXTENSION_MIME_FALLBACK = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}


def safe_filename(name: str | None) -> str:
    """Collapse a client-supplied filename to just its basename before it
    becomes part of a storage path. Path(...).name strips any directory
    components — a crafted "../../other-user-id/x" collapses to just "x"
    rather than escaping its folder. This runs on the service-role write path
    (storage.upload/db.insert both bypass RLS), so a filename is fully
    trusted otherwise."""
    base = Path(name or "upload").name
    return "".join(c for c in base if c.isprintable()) or "upload"


def resolve_mime_type(filename: str, declared: str | None) -> str:
    """The MIME type to treat an upload as, or raise ValueError if unsupported."""
    mime = declared or ""
    if mime in GENERIC_MIME_TYPES:
        ext = Path(filename).suffix.lower()
        mime = EXTENSION_MIME_FALLBACK.get(ext, mime or "application/octet-stream")
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"unsupported file type: {mime}. Allowed: .txt, .md, .pdf")
    return mime


def extract_text(content: bytes, mime_type: str) -> str:
    """Best-effort text extraction. Anything that fails to parse raises — the
    caller decides whether that is fatal (ingest: skip) or degraded (tutor:
    keep the file, contribute no context)."""
    if mime_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content.decode("utf-8", errors="replace")
