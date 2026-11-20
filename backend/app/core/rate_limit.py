"""Lightweight in-memory sliding-window rate limiter for API abuse protection."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemorySlidingWindowRateLimiter:
    """Thread-safe per-key sliding-window rate limiter bounded by key capacity."""

    def __init__(self, *, window_seconds: float = 60.0, max_keys: int = 8192) -> None:
        self._window_seconds = window_seconds
        self._max_keys = max_keys
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int) -> RateLimitDecision:
        """Consume one slot for `key` if under `limit`, otherwise return denial metadata."""
        if limit <= 0:
            return RateLimitDecision(allowed=True, limit=limit, remaining=0, retry_after_seconds=0)

        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            if len(self._buckets) > self._max_keys:
                self._evict_expired(cutoff)

            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                oldest = bucket[0]
                retry_after = max(1, int(self._window_seconds - (now - oldest)) + 1)
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            bucket.append(now)
            remaining = max(0, limit - len(bucket))
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=0,
            )

    def _evict_expired(self, cutoff: float) -> None:
        stale_keys = [
            key for key, bucket in self._buckets.items() if not bucket or bucket[-1] <= cutoff
        ]
        for key in stale_keys:
            self._buckets.pop(key, None)
