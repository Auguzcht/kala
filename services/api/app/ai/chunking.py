from __future__ import annotations


def chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> list[str]:
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