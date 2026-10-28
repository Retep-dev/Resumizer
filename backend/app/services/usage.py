"""Usage limits for a free public app: per-client rate limits, global daily caps,
concurrency limits and a duplicate-analysis cache.

Everything is in memory and per process (Render runs one instance on the free
tier). Client IPs are hashed with a per-process salt and never stored raw.
All limits can be tuned with environment variables.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import threading
import time
from collections import OrderedDict, defaultdict, deque
from typing import Deque, Dict, Optional, Tuple


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Limits:
    ANALYZE_PER_HOUR = _env_int("ANALYZE_LIMIT_PER_HOUR", 5)
    ANALYZE_PER_DAY = _env_int("ANALYZE_LIMIT_PER_DAY", 15)
    CHAT_PER_HOUR = _env_int("CHAT_LIMIT_PER_HOUR", 40)
    CHAT_PER_SESSION = _env_int("CHAT_LIMIT_PER_SESSION", 30)
    GLOBAL_ANALYZE_PER_DAY = _env_int("GLOBAL_ANALYZE_LIMIT_PER_DAY", 300)
    GLOBAL_CHAT_PER_DAY = _env_int("GLOBAL_CHAT_LIMIT_PER_DAY", 2000)
    MAX_CONCURRENT_ANALYSES = _env_int("MAX_CONCURRENT_ANALYSES", 3)
    MAX_CONCURRENT_CHATS = _env_int("MAX_CONCURRENT_CHATS", 6)
    QUEUE_WAIT_SECONDS = float(os.getenv("QUEUE_WAIT_SECONDS", "20"))
    PIPELINE_TIMEOUT_SECONDS = float(os.getenv("PIPELINE_TIMEOUT_SECONDS", "180"))
    CHAT_TIMEOUT_SECONDS = float(os.getenv("CHAT_TIMEOUT_SECONDS", "90"))
    DUPLICATE_CACHE_SECONDS = _env_int("DUPLICATE_CACHE_SECONDS", 6 * 3600)


class LimitExceeded(Exception):
    def __init__(self, code: str, message: str, retry_after: int):
        super().__init__(message)
        self.code, self.message, self.retry_after = code, message, retry_after


_SALT = secrets.token_hex(16)


def client_key(forwarded_for: Optional[str], remote: Optional[str]) -> str:
    """Hashed client identity: the first X-Forwarded-For hop (Render's proxy sets it), else the socket address."""
    ip = (forwarded_for or "").split(",")[0].strip() or (remote or "unknown")
    return hashlib.sha256(f"{_SALT}:{ip}".encode()).hexdigest()[:16]


class SlidingWindow:
    def __init__(self):
        self.lock = threading.Lock()
        self.hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float, now: Optional[float] = None) -> int:
        """0 if allowed (and recorded), else seconds until a slot frees up."""
        now = now or time.time()
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(q[0] + window - now) + 1)
            q.append(now)
            if len(self.hits) > 20000:  # bound memory under a flood of distinct clients
                for k in list(self.hits)[:5000]:
                    if not self.hits[k]:
                        del self.hits[k]
            return 0

    def reset(self):
        with self.lock:
            self.hits.clear()


WINDOWS = SlidingWindow()
DAY, HOUR = 86400.0, 3600.0


def check_analyze(client: str):
    for key, limit, window, code, msg in (
        ("global:analyze", Limits.GLOBAL_ANALYZE_PER_DAY, DAY, "daily_capacity_reached",
         "Resumizer has reached today's limit of free analyses. Please try again tomorrow."),
        (f"{client}:analyze:h", Limits.ANALYZE_PER_HOUR, HOUR, "rate_limited",
         f"You've run {Limits.ANALYZE_PER_HOUR} analyses in the last hour. Please wait before running another."),
        (f"{client}:analyze:d", Limits.ANALYZE_PER_DAY, DAY, "rate_limited",
         f"You've reached today's limit of {Limits.ANALYZE_PER_DAY} analyses. Please come back tomorrow."),
    ):
        wait = WINDOWS.check(key, limit, window)
        if wait:
            raise LimitExceeded(code, msg, wait)


def check_chat(client: str, session_id: str):
    for key, limit, window, code, msg in (
        ("global:chat", Limits.GLOBAL_CHAT_PER_DAY, DAY, "daily_capacity_reached",
         "The coach has reached today's limit of free messages. Please try again tomorrow."),
        (f"{client}:chat:h", Limits.CHAT_PER_HOUR, HOUR, "rate_limited",
         "You're sending messages faster than the free coach allows. Please wait a little and try again."),
        (f"session:{session_id}:chat", Limits.CHAT_PER_SESSION, DAY, "rate_limited",
         f"This analysis has reached its limit of {Limits.CHAT_PER_SESSION} coach messages. Run a new analysis to keep chatting."),
    ):
        wait = WINDOWS.check(key, limit, window)
        if wait:
            raise LimitExceeded(code, msg, wait)


class Gate:
    """Caps simultaneous work; waits briefly, then reports 'busy' rather than queueing forever."""

    def __init__(self, size: int):
        self.size = size
        self._sem: Optional[asyncio.Semaphore] = None

    def _semaphore(self) -> asyncio.Semaphore:
        if self._sem is None:
            self._sem = asyncio.Semaphore(self.size)
        return self._sem

    async def __aenter__(self):
        try:
            await asyncio.wait_for(self._semaphore().acquire(), timeout=Limits.QUEUE_WAIT_SECONDS)
        except asyncio.TimeoutError:
            raise LimitExceeded("busy", "Resumizer is busy right now. Please try again in a minute.", 30)
        return self

    async def __aexit__(self, *exc):
        self._semaphore().release()


ANALYSIS_GATE = Gate(Limits.MAX_CONCURRENT_ANALYSES)
CHAT_GATE = Gate(Limits.MAX_CONCURRENT_CHATS)


class DuplicateCache:
    """Same resume + same posting within a few hours → the earlier result, with no AI calls."""

    def __init__(self, size: int = 300):
        self.lock = threading.Lock()
        self.items: "OrderedDict[str, Tuple[float, str, dict]]" = OrderedDict()
        self.size = size

    @staticmethod
    def key(resume_text: str, job_description: str) -> str:
        norm = lambda t: " ".join((t or "").split()).lower()  # noqa: E731
        return hashlib.sha256((norm(resume_text) + "\x00" + norm(job_description)).encode()).hexdigest()

    def get(self, key: str) -> Optional[Tuple[str, dict]]:
        with self.lock:
            hit = self.items.get(key)
            if not hit or time.time() - hit[0] > Limits.DUPLICATE_CACHE_SECONDS:
                self.items.pop(key, None)
                return None
            return hit[1], hit[2]

    def put(self, key: str, session_id: str, analysis: dict):
        with self.lock:
            self.items[key] = (time.time(), session_id, analysis)
            self.items.move_to_end(key)
            while len(self.items) > self.size:
                self.items.popitem(last=False)

    def clear(self):
        with self.lock:
            self.items.clear()


DUPLICATES = DuplicateCache()
