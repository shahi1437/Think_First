"""In-process async notification hub for sub-second outbound worker wakeups.

On Render Free (single Uvicorn worker), this wakes a long-polling outbound
execution worker immediately when a student submits code, and wakes synchronous
callers immediately when the worker posts results, avoiding busy-loop DB polling.
"""

from __future__ import annotations

import asyncio
from uuid import UUID


class ExecutionQueueHub:
    """Coordinates lightweight asyncio events between enqueue and worker long-poll."""

    def __init__(self) -> None:
        self._new_job_waiters: set[asyncio.Event] = set()
        self._job_done_waiters: dict[UUID, set[asyncio.Event]] = {}

    def notify_new_job(self) -> None:
        for ev in list(self._new_job_waiters):
            ev.set()

    async def wait_for_new_job(self, timeout_seconds: float) -> bool:
        if timeout_seconds <= 0:
            return False
        ev = asyncio.Event()
        self._new_job_waiters.add(ev)
        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout_seconds)
            return True
        except TimeoutError:
            return False
        finally:
            self._new_job_waiters.discard(ev)

    def notify_job_done(self, job_id: UUID) -> None:
        waiters = self._job_done_waiters.get(job_id)
        if not waiters:
            return
        for ev in list(waiters):
            ev.set()

    async def wait_for_job_done(self, job_id: UUID, timeout_seconds: float) -> bool:
        if timeout_seconds <= 0:
            return False
        ev = asyncio.Event()
        self._job_done_waiters.setdefault(job_id, set()).add(ev)
        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout_seconds)
            return True
        except TimeoutError:
            return False
        finally:
            waiters = self._job_done_waiters.get(job_id)
            if waiters is not None:
                waiters.discard(ev)
                if not waiters:
                    self._job_done_waiters.pop(job_id, None)


_queue_hub = ExecutionQueueHub()


def get_execution_queue_hub() -> ExecutionQueueHub:
    return _queue_hub
