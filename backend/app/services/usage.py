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
    # Per person (hashed IP). Analyses are the expensive part of the free quota.
    ANALYZE_PER_DAY = _env_int("ANALYZE_LIMIT_PER_DAY", 3)
    ANALYZE_PER_HOUR = _env_int("ANALYZE_LIMIT_PER_HOUR", ANALYZE_PER_DAY)
    CHAT_PER_SESSION = _env_int("CHAT_LIMIT_PER_SESSION", 10)   # coach messages per analysis
    CHAT_PER_DAY = _env_int("CHAT_LIMIT_PER_DAY", 20)           # coach messages per person per day
    CHAT_PER_HOUR = _env_int("CHAT_LIMIT_PER_HOUR", CHAT_PER_DAY)
    # Whole app. Unset = worked out from the free provider quota (see global_limits()).
    GLOBAL_ANALYZE_PER_DAY = _env_int("GLOBAL_ANALYZE_LIMIT_PER_DAY", 0)
    GLOBAL_CHAT_PER_DAY = _env_int("GLOBAL_CHAT_LIMIT_PER_DAY", 0)
    MAX_CONCURRENT_ANALYSES = _env_int("MAX_CONCURRENT_ANALYSES", 0)  # 0 = from the per-minute token limit
    MAX_CONCURRENT_CHATS = _env_int("MAX_CONCURRENT_CHATS", 4)
    QUEUE_WAIT_SECONDS = float(os.getenv("QUEUE_WAIT_SECONDS", "45"))
    PIPELINE_TIMEOUT_SECONDS = float(os.getenv("PIPELINE_TIMEOUT_SECONDS", "240"))
    CHAT_TIMEOUT_SECONDS = float(os.getenv("CHAT_TIMEOUT_SECONDS", "90"))
    DUPLICATE_CACHE_SECONDS = _env_int("DUPLICATE_CACHE_SECONDS", 6 * 3600)
    # Measured on Groq with the production chains (eval round 2, 30 Oct 2026, 7 fictional resumes): averages of
    # 2,106 (analysis), 2,883 (rewrite), 2,338 (interview) and 2,770 per coach message, rounded up by ~25%
    # because real resumes are longer than the fictional ones. Override with JOURNEY_TOKENS="analysis:2600,...".
    JOURNEY_TOKENS_DEFAULT = {"analysis": 2600, "rewrite": 3600, "interview": 2900, "coach": 3500}
    EXPECTED_COACH_MESSAGES = _env_int("EXPECTED_COACH_MESSAGES", 4)  # per analysis, for sizing the global caps
    FALLBACK_GLOBAL = (300, 2000)  # used only when no chain model has a published quota (e.g. evaluation)


def journey_tokens() -> Dict[str, int]:
    out = dict(Limits.JOURNEY_TOKENS_DEFAULT)
    for part in [p.strip() for p in os.getenv("JOURNEY_TOKENS", "").split(",") if p.strip()]:
        k, _, v = part.partition(":")
        if v.strip().isdigit():
            out[k.strip().lower()] = int(v)
    return out


def global_limits() -> Dict[str, object]:
    """Daily caps for the whole app, sized to the free quota of the first usable model of each task.

    One "session" = one analysis + EXPECTED_COACH_MESSAGES coach messages. For each model, its daily token
    budget (minus headroom) divided by what one session costs on that model gives the sessions it can serve;
    the smallest wins. Fallback models are not counted, so they are spare capacity for spikes, not plan.
    """
    from app.config import settings
    from app.llm.router import QUOTA_HEADROOM, _base_model, provider_status, quotas

    tokens, q = journey_tokens(), quotas()
    demand: Dict[str, float] = {}
    per_minute: Dict[str, float] = {}
    primaries = {}
    for task in settings.TASKS:
        primary = next((f"{p}:{_base_model(m)}" for p, m in settings.task_chain(task) if provider_status(p)[0]), None)
        primaries[task] = primary
        if not primary:
            continue
        cost = tokens.get(task, 0) * (Limits.EXPECTED_COACH_MESSAGES if task == "coach" else 1)
        demand[primary] = demand.get(primary, 0) + cost
        if task != "coach":
            per_minute[primary] = per_minute.get(primary, 0) + tokens.get(task, 0)
    sessions, basis = [], []
    for model, need in demand.items():
        tpd = (q.get(model) or {}).get("tpd")
        if tpd and need:
            n = int(tpd * QUOTA_HEADROOM // need)
            sessions.append(n)
            basis.append(f"{model}: {tpd:,} tokens/day x {QUOTA_HEADROOM:.0%} / {int(need):,} per session = {n}")
    if sessions:
        analyses = max(1, min(sessions))
        chats = analyses * Limits.EXPECTED_COACH_MESSAGES
        tpms = [(q.get(m) or {}).get("tpm") for m in per_minute]
        conc = max(1, min(int(t // per_minute[m]) for m, t in zip(per_minute, tpms) if t) if any(tpms) else 1)
    else:
        analyses, chats = Limits.FALLBACK_GLOBAL
        conc = 3
        basis.append("no AI model with a published free quota is ready (no key, or evaluation-only models); "
                     "fixed fallback caps, which only limit rule-based or evaluation use")
    return {
        "analyses_per_day": Limits.GLOBAL_ANALYZE_PER_DAY or analyses,
        "coach_messages_per_day": Limits.GLOBAL_CHAT_PER_DAY or chats,
        "concurrent_analyses": Limits.MAX_CONCURRENT_ANALYSES or conc,
        "overridden": [k for k, v in (("analyses_per_day", Limits.GLOBAL_ANALYZE_PER_DAY), ("coach_messages_per_day", Limits.GLOBAL_CHAT_PER_DAY),
                                      ("concurrent_analyses", Limits.MAX_CONCURRENT_ANALYSES)) if v],
        "basis": basis, "primary_models": primaries, "journey_tokens": tokens,
        "expected_coach_messages_per_analysis": Limits.EXPECTED_COACH_MESSAGES,
    }


def per_user_limits() -> Dict[str, int]:
    return {"analyses_per_day": Limits.ANALYZE_PER_DAY, "analyses_per_hour": Limits.ANALYZE_PER_HOUR,
            "coach_messages_per_analysis": Limits.CHAT_PER_SESSION, "coach_messages_per_day": Limits.CHAT_PER_DAY}


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
    g = global_limits()
    for key, limit, window, code, msg in (
        ("global:analyze", g["analyses_per_day"], DAY, "daily_capacity_reached",
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
    g = global_limits()
    for key, limit, window, code, msg in (
        ("global:chat", g["coach_messages_per_day"], DAY, "daily_capacity_reached",
         "The coach has reached today's limit of free messages. Please try again tomorrow."),
        (f"{client}:chat:h", Limits.CHAT_PER_HOUR, HOUR, "rate_limited",
         "You're sending messages faster than the free coach allows. Please wait a little and try again."),
        (f"{client}:chat:d", Limits.CHAT_PER_DAY, DAY, "rate_limited",
         f"You've reached today's limit of {Limits.CHAT_PER_DAY} coach messages. Please come back tomorrow."),
        (f"session:{session_id}:chat", Limits.CHAT_PER_SESSION, DAY, "rate_limited",
         f"This analysis has reached its limit of {Limits.CHAT_PER_SESSION} coach messages. Run a new analysis to keep chatting."),
    ):
        wait = WINDOWS.check(key, limit, window)
        if wait:
            raise LimitExceeded(code, msg, wait)


class Gate:
    """Caps simultaneous work; waits briefly, then reports 'busy' rather than queueing forever."""

    def __init__(self, size):
        self._size = size  # an int, or a function returning one (worked out on first use)
        self._sem: Optional[asyncio.Semaphore] = None

    @property
    def size(self) -> int:
        return self._size() if callable(self._size) else self._size

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


ANALYSIS_GATE = Gate(lambda: int(global_limits()["concurrent_analyses"]))
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
