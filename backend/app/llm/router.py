"""Which model handles which task.

Each task (analysis, rewrite, interview, coach) has its own ordered chain of
"provider:model" entries (see Settings.task_chain). A provider is used only if
its key is configured on the server and, for anything other than NVIDIA,
ALLOW_PAID_PROVIDERS is "true". Entries that can't be used are skipped and
reported by /api/v1/status, so a misconfiguration is visible rather than silent.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.llm.provider import (
    AnthropicChatClient, ChatClient, Completion, NvidiaChatClient, OpenAICompatibleClient, ProviderError,
)

log = logging.getLogger("resumizer.llm")

PROVIDERS = ("nvidia", "openai", "openrouter", "anthropic")


def provider_status(provider: str) -> Tuple[bool, str]:
    """(usable, reason) for a provider name. Never includes a key."""
    if provider not in PROVIDERS:
        return False, f"unknown provider '{provider}'"
    if provider != "nvidia" and not settings.ALLOW_PAID_PROVIDERS:
        return False, "off: ALLOW_PAID_PROVIDERS is not 'true'"
    key = {"nvidia": settings.NVIDIA_API_KEY, "openai": settings.OPENAI_API_KEY,
           "openrouter": settings.OPENROUTER_API_KEY, "anthropic": settings.ANTHROPIC_API_KEY}[provider]
    if not key or "your-key-here" in key.lower():
        return False, f"off: no {provider.upper()}_API_KEY on the server"
    return True, "ready"


_provider_clients: Dict[str, ChatClient] = {}


def provider_client(provider: str) -> ChatClient:
    """One HTTP client per provider; models are passed per call by ChainClient."""
    if provider not in _provider_clients:
        t = settings.LLM_TIMEOUT_SECONDS
        if provider == "nvidia":
            c = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=[], base_url=settings.NVIDIA_BASE_URL, timeout=t)
        elif provider == "openai":
            c = OpenAICompatibleClient(api_key=settings.OPENAI_API_KEY, models=[], base_url=settings.OPENAI_BASE_URL, timeout=t, provider="openai")
        elif provider == "openrouter":
            c = OpenAICompatibleClient(api_key=settings.OPENROUTER_API_KEY, models=[], base_url="https://openrouter.ai/api/v1", timeout=t, provider="openrouter")
        elif provider == "anthropic":
            c = AnthropicChatClient(api_key=settings.ANTHROPIC_API_KEY, models=[], timeout=t)
        else:
            raise ProviderError("not_configured", f"Unknown provider {provider}")
        _provider_clients[provider] = c
    return _provider_clients[provider]


@dataclass
class ChainClient(ChatClient):
    """Tries each (provider, model) in order; moves on when one is unusable or fails."""
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
        usable = [(p, m) for p, m in self.entries if provider_status(p)[0]]
        if not usable:
            reasons = "; ".join(f"{p}: {provider_status(p)[1]}" for p, _ in self.entries)
            raise ProviderError("not_configured", f"No usable model for {self.task} ({reasons})")
        for i, (provider, model) in enumerate(usable):
            # A per-call copy: shares the HTTP session and the retired-model set, safe for parallel stages.
            client = dataclasses.replace(provider_client(provider), models=[model])
            try:
                return await client.complete(messages, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)
            except ProviderError as e:
                last = e
                if e.kind == "bad_request" and i == len(usable) - 1:
                    raise
                log.warning("%s: %s:%s failed (%s); trying next", self.task, provider, model, e.kind)
        raise last  # type: ignore[misc]


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
    """Per-task chain with each entry's readiness, for /api/v1/status. No secrets."""
    out = {}
    for task in settings.TASKS:
        out[task] = [{"provider": p, "model": m, "ready": provider_status(p)[0], "note": provider_status(p)[1]}
                     for p, m in settings.task_chain(task)]
    return out


def client_from_spec(spec: str, timeout: Optional[float] = None) -> ChainClient:
    """'nvidia:vendor/model,anthropic:claude-x' → a chain (used by the evaluation)."""
    entries = []
    for part in [s.strip() for s in spec.split(",") if s.strip()]:
        provider, _, model = part.partition(":") if ":" in part.split("/")[0] else ("nvidia", "", part)
        entries.append((provider.lower(), model))
    if timeout:
        settings.LLM_TIMEOUT_SECONDS = timeout
        _provider_clients.clear()
    return ChainClient(task="eval", entries=entries)
