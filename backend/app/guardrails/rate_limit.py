"""Token-usage rate limiting for the coach.

Two independent limits per identity (default: a single local user):
  * requests-per-minute  — a sliding-window counter, stops bursty abuse.
  * daily token budget    — input+output tokens; reserve an estimate before the
    call, then reconcile with the real usage afterwards.

In-memory and thread-safe — fine for this single-process app; swap the backing
dict for Redis if you scale out. Limits come from config/.env.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from ..config import get_settings

_DAY = 86_400
_MINUTE = 60


class RateLimitError(RuntimeError):
    """Raised when a limit is exceeded (caller maps to HTTP 429)."""
    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TokenRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._req_times: dict[str, deque[float]] = defaultdict(deque)
        # identity -> (window_start_epoch_day, tokens_used)
        self._tokens: dict[str, list] = defaultdict(lambda: [0.0, 0])

    def _settings(self):
        return get_settings()

    def check(self, identity: str, estimated_tokens: int) -> None:
        """Raise RateLimitError if this request would exceed a limit. Call
        before invoking the model; reserves the estimated tokens."""
        s = self._settings()
        now = time.time()
        with self._lock:
            # --- requests / minute (sliding window) ---
            q = self._req_times[identity]
            while q and now - q[0] > _MINUTE:
                q.popleft()
            if len(q) >= s.coach_max_requests_per_min:
                raise RateLimitError(
                    f"rate limit: max {s.coach_max_requests_per_min} requests/min",
                    retry_after=int(_MINUTE - (now - q[0])) + 1)
            q.append(now)

            # --- daily token budget ---
            bucket = self._tokens[identity]
            if now - bucket[0] > _DAY:
                bucket[0], bucket[1] = now, 0
            if bucket[1] + estimated_tokens > s.coach_daily_token_budget:
                raise RateLimitError(
                    f"daily token budget exhausted "
                    f"({s.coach_daily_token_budget} tokens). Try again tomorrow.",
                    retry_after=int(_DAY - (now - bucket[0])) + 1)
            bucket[1] += estimated_tokens          # reserve the estimate

    def reconcile(self, identity: str, estimated_tokens: int, actual_tokens: int) -> None:
        """Adjust the reserved estimate to the real usage after the call."""
        with self._lock:
            bucket = self._tokens[identity]
            bucket[1] = max(0, bucket[1] - estimated_tokens + max(0, actual_tokens))

    def remaining(self, identity: str) -> int:
        s = self._settings()
        with self._lock:
            return max(0, s.coach_daily_token_budget - self._tokens[identity][1])


coach_rate_limiter = TokenRateLimiter()
