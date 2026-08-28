"""Concurrency helper for the learn loop's per-item generation calls.

Why this exists: diagnostic, flashcards-deck top-up, and guided-lesson step
generation all fan out one Bedrock/RAG call per skill or per step, and until
now did it as a plain Python for-loop, i.e. fully serial. Each call is
network I/O (httpx or boto3, a few seconds at typical model latency), so a
10-skill diagnostic meant 10 sequential round trips, easily minutes. That is
the actual cause of the multi-minute page loads, not a frontend problem.

Every call site this wraps opens its own httpx.Client or boto3 client per
call (see ai/bedrock.py, db/supabase.py) with no shared mutable state, so
running them on a thread pool is safe: each call is self-contained I/O, and
Python releases the GIL during it.

This intentionally preserves the exact exception semantics of the plain
list-comprehension it replaces: if any call raises, that exception
propagates to the caller, same as `[fn(i) for i in items]` would. This is
NOT a best-effort/swallow-errors helper — every generator this wraps
(generate_question, _generate_step_content, etc.) already degrades
internally on a model failure rather than raising, so an exception reaching
here means a genuine infrastructure error (e.g. a DB write failure), which
should still surface loudly, not be silently dropped from a batch.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def map_concurrent(fn: Callable[[T], R], items: list[T], *, max_workers: int = 8) -> list[R]:
    """Apply fn to each item on a thread pool, returning results in the same
    order as `items`. Semantically equivalent to `[fn(i) for i in items]`,
    just parallel. Empty input short-circuits without spinning up a pool."""
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        futures = [pool.submit(fn, item) for item in items]
        return [f.result() for f in futures]
