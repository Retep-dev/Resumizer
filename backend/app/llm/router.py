"""Free-only model routing.

Each task (analysis, rewrite, interview, coach) has an ordered chain of
"provider:model" entries (Settings.task_chain). Only free providers exist here:

  nvidia    NVIDIA API Catalog trial key. Its terms allow internal testing and
            evaluation only, so /status flags it for anything public.
  groq      Groq free tier (key with no payment method attached cannot be billed).
  cerebras  Cerebras free tier (same).

There is no paid provider in the code, so none can be enabled by configuration.
Before each call the router skips entries that are not configured, are over
their daily request cap (to stay inside free quotas), or are cooling down after
repeated failures or a 429. If nothing is usable the call fails with a clear
error and the pipeline falls back to its rule-based result.
"""
from __future__ import annotations

import dataclasses
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.llm.provider import ChatClient, Completion, NvidiaChatClient, OpenAICompatibleClient, ProviderError

log = logging.getLogger("resumizer.llm")

FREE_PROVIDERS: Dict[str, Dict[str, str]] = {
    "nvidia": {"base": "", "terms": "free trial: NVIDIA's terms allow internal testing and evaluation only, not production"},
    "groq": {"base": "https://api.groq.com/openai/v1", "terms": "free tier; Groq does not train on inputs or outputs; enable Zero Data Retention"},
    "cerebras": {"base": "https://api.cerebras.ai/v1", "terms": "free tier; Cerebras states it does not retain inputs or outputs"},
}
PROVIDERS = tuple(FREE_PROVIDERS)

FAILS_BEFORE_COOLDOWN = int(os.getenv("MODEL_FAILS_BEFORE_COOLDOWN", "3"))
COOLDOWN_SECONDS = float(os.getenv("MODEL_COOLDOWN_SECONDS", "300"))


def _key(provider: str) -> str:
    return {"nvidia": settings.NVIDIA_API_KEY, "groq": settings.GROQ_API_KEY, "cerebras": settings.CEREBRAS_API_KEY}.get(provider, "")


def provider_status(provider: str) -> Tuple[bool, str]:
    """(usable, reason) for a provider name. Never includes a key."""
    if provider not in FREE_PROVIDERS:
        return False, f"not allowed: '{provider}' is not a free provider supported by Resumizer"
    key = _key(provider)
    if not key or "your-key-here" in key.lower():
        return False, f"off: no {provider.upper()}_API_KEY on the server"
    return True, "ready"


def daily_caps() -> Dict[str, int]:
    """Requests per UTC day per 'provider' or 'provider:model', from DAILY_REQUEST_CAPS="groq:900,cerebras:400"."""
    caps = {}
    for part in [p.strip() for p in os.getenv("DAILY_REQUEST_CAPS", "").split(",") if p.strip()]:
        name, _, n = part.rpartition(":")
        if name and n.isdigit():
            caps[name.lower()] = int(n)
    return caps


class Health:
    """Per-model usage and failure bookkeeping (in memory, per process)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.day = ""
        self.used: Dict[str, int] = {}
        self.fails: Dict[str, int] = {}
        self.cool_until: Dict[str, float] = {}

    def _roll(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.day:
            self.day, self.used = today, {}

    def available(self, provider: str, model: str) -> Tuple[bool, str]:
        with self.lock:
            self._roll()
            key = f"{provider}:{model}"
            if self.cool_until.get(key, 0) > time.time():
                return False, "cooling down after repeated failures"
            caps = daily_caps()
            for name in (key, provider):
                cap = caps.get(name)
                used = self.used.get(name, 0)
                if cap is not None and used >= cap:
                    return False, f"daily free quota reached ({used}/{cap})"
            return True, "ready"

    def record(self, provider: str, model: str, ok: bool, kind: str = ""):
        with self.lock:
            self._roll()
            key = f"{provider}:{model}"
            for name in (key, provider):
                self.used[name] = self.used.get(name, 0) + 1
            if ok:
                self.fails[key] = 0
                return
            if kind == "rate_limited":
                self.cool_until[key] = time.time() + 60
            self.fails[key] = self.fails.get(key, 0) + 1
            if self.fails[key] >= FAILS_BEFORE_COOLDOWN:
                self.cool_until[key] = time.time() + COOLDOWN_SECONDS
                self.fails[key] = 0
                log.warning("%s cooling down for %ss after %s failures", key, COOLDOWN_SECONDS, FAILS_BEFORE_COOLDOWN)

    def snapshot(self) -> Dict[str, object]:
        with self.lock:
            self._roll()
            now = time.time()
            return {"day": self.day, "requests_today": dict(self.used),
                    "cooling_down": {k: round(v - now) for k, v in self.cool_until.items() if v > now}}


HEALTH = Health()
_provider_clients: Dict[str, ChatClient] = {}


def provider_client(provider: str) -> ChatClient:
    """One HTTP client per provider; models are passed per call by ChainClient."""
    if provider not in _provider_clients:
        if provider not in FREE_PROVIDERS:
            raise ProviderError("not_configured", f"'{provider}' is not a free provider supported by Resumizer")
        t = settings.LLM_TIMEOUT_SECONDS
        if provider == "nvidia":
            c = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=[], base_url=settings.NVIDIA_BASE_URL, timeout=t)
        else:
            c = OpenAICompatibleClient(api_key=_key(provider), models=[], base_url=FREE_PROVIDERS[provider]["base"], timeout=t, provider=provider)
        _provider_clients[provider] = c
    return _provider_clients[provider]


@dataclass
class ChainClient(ChatClient):
    """Tries each free (provider, model) in order; skips unusable ones; never anything paid."""
    task: str
    entries: List[Tuple[str, str]]
    skipped: List[Dict[str, str]] = field(default_factory=list)

    @property
    def retired(self) -> set:
        out = set()
        for p in {p for p, _ in self.entries}:
            if p in _provider_clients:
                out |= set(getattr(_provider_clients[p], "retired", set()))
        return out

    async def complete(self, messages, *, temperature=0.1, max_tokens=2048, json_mode=False) -> Completion:
        last: Optional[ProviderError] = None
        reasons = []
        for provider, model in self.entries:
            ok, why = provider_status(provider)
            if ok:
                ok, why = HEALTH.available(provider, model)
            if not ok:
                reasons.append(f"{provider}:{model} {why}")
                continue
            # A per-call copy shares the HTTP session and retired set; safe for parallel stages.
            client = dataclasses.replace(provider_client(provider), models=[model])
            try:
                out = await client.complete(messages, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)
                HEALTH.record(provider, model, True)
                return out
            except ProviderError as e:
                HEALTH.record(provider, model, False, e.kind)
                last = e
                reasons.append(f"{provider}:{model} {e.kind}")
                log.warning("%s: %s:%s failed (%s); trying next", self.task, provider, model, e.kind)
        if last is None:
            quota = any("quota" in r for r in reasons)
            raise ProviderError("rate_limited" if quota else "not_configured",
                                ("Today's free AI capacity is used up" if quota else "No free AI model is available")
                                + f" for {self.task} (" + "; ".join(reasons) + ")")
        raise last


_task_clients: Dict[str, ChatClient] = {}
_override: Dict[Optional[str], ChatClient] = {}


def get_client(task: str = "analysis") -> ChatClient:
    if task in _override:
        return _override[task]
    if None in _override:
        return _override[None]
    if task not in _task_clients:
        _task_clients[task] = ChainClient(task=task, entries=settings.task_chain(task))
    return _task_clients[task]


def set_client(client: Optional[ChatClient], task: Optional[str] = None) -> None:
    """Swap the client (tests, evaluation). Without a task, applies to every task; None clears."""
    if client is None:
        if task is None:
            _override.clear()
        else:
            _override.pop(task, None)
    else:
        _override[task] = client


def routing_status() -> Dict[str, List[Dict[str, object]]]:
    """Per-task chain with each entry's readiness and terms note, for /api/v1/status. No secrets."""
    out = {}
    for task in settings.TASKS:
        rows = []
        for p, m in settings.task_chain(task):
            ok, note = provider_status(p)
            if ok:
                ok, note = HEALTH.available(p, m)
            rows.append({"provider": p, "model": m, "ready": ok, "note": note,
                         "terms": FREE_PROVIDERS.get(p, {}).get("terms", "not allowed")})
        out[task] = rows
    return out


def client_from_spec(spec: str, timeout: Optional[float] = None) -> ChainClient:
    """'nvidia:vendor/model,groq:model' → a chain (used by the evaluation)."""
    entries = []
    for part in [s.strip() for s in spec.split(",") if s.strip()]:
        provider, _, model = part.partition(":") if ":" in part.split("/")[0] else ("nvidia", "", part)
        entries.append((provider.lower(), model))
    if timeout:
        settings.LLM_TIMEOUT_SECONDS = timeout
        _provider_clients.clear()
    return ChainClient(task="eval", entries=entries)
