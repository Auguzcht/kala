"""Opt-in elapsed-time budget for tutor; synchronous callers keep their defaults.

HTTPX timeouts bound inactivity, not elapsed time. run() separately bounds how
long the async handler waits, including worker queueing. Cancellation abandons
an in-flight synchronous operation, not its thread or remote side effects.
"""
from __future__ import annotations

from functools import partial
from time import monotonic

import anyio


class TutorTimeout(Exception):
    """No answer was available within the tutor request budget."""

    def __init__(self):
        super().__init__("The tutor took too long to respond. Please try again.")


class RequestBudget:
    def __init__(self, seconds: float = 26.0, reserve: float = 3.0):
        self.started = monotonic()
        self.deadline = self.started + seconds
        self.reserve = reserve
        self.timings: dict[str, float] = {}
        self.provider_role = "chat"
        self.fallback_used = False
        self.outcome = "error"
        self.closed = False

    def remaining(self) -> float:
        return max(0.0, self.deadline - monotonic()) if not self.closed else 0.0

    def timeout(self, current: float) -> float:
        available = self.remaining() - self.reserve
        if available <= 0:
            raise TutorTimeout()
        return min(current, available)

    async def run(self, stage: str, fn, /, *args, **kwargs):
        started = monotonic()
        try:
            # The worker repeats timeout() when constructing each outbound
            # request, so waiting for worker capacity cannot stale the timeout.
            with anyio.fail_after(self.timeout(float("inf"))):
                return await anyio.to_thread.run_sync(
                    partial(fn, *args, budget=self, **kwargs), abandon_on_cancel=True,
                )
        except TimeoutError:
            self.closed = True
            raise TutorTimeout() from None
        finally:
            self.timings[f"{stage}_ms"] = (monotonic() - started) * 1000
