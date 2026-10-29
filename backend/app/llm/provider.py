"""NVIDIA API Catalog chat client (OpenAI-compatible /v1/chat/completions).

Why not LangChain: the previous LangChain wrappers hid provider errors (a
retired model raised a generic exception that every agent swallowed). This
client classifies failures so the pipeline can report them honestly, and it
walks a configured chain of models when one is retired.

The API key is only ever placed in the Authorization header. It is never
logged, included in exceptions or returned to callers.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import requests

from app.config import settings

log = logging.getLogger("resumizer.llm")


class ProviderError(Exception):
    """A classified failure talking to the model provider.

    kind: 'not_configured' | 'auth' | 'model_unavailable' | 'rate_limited' |
          'timeout' | 'network' | 'server' | 'bad_request' | 'bad_response'
    """

    def __init__(self, kind: str, message: str, model: Optional[str] = None, status: Optional[int] = None,
                 retry_after: Optional[float] = None, scope: Optional[str] = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.model = model
        self.status = status
        self.retry_after = retry_after  # seconds, from the provider's Retry-After header
        self.scope = scope              # 'minute' or 'day' for rate limits, when the provider says which

    @property
    def retryable(self) -> bool:
        return self.kind in {"rate_limited", "timeout", "network", "server"}

    def public(self) -> Dict[str, Optional[str]]:
        return {"kind": self.kind, "message": self.message, "model": self.model}


@dataclass
class Completion:
    text: str
    model: str
    provider: str = "nvidia"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    quota: Dict[str, str] = field(default_factory=dict)  # provider's x-ratelimit-* headers (remaining requests/tokens)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _clean_message(text: str, limit: int = 300) -> str:
    """Strip anything that could be a credential and cap length."""
    t = re.sub(r"nvapi-[A-Za-z0-9_\-]+", "nvapi-***", text or "")
    t = re.sub(r"gsk_[A-Za-z0-9]+", "gsk_***", t)
    t = re.sub(r"csk-[A-Za-z0-9]+", "csk-***", t)
    t = re.sub(r"(?i)bearer\s+[A-Za-z0-9_\-.]+", "Bearer ***", t)
    t = " ".join(t.split())
    return t[:limit]


class ChatClient:
    """Interface the agents depend on. Tests provide a fake implementation."""

    async def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.1,
                       max_tokens: int = 2048, json_mode: bool = False) -> Completion:  # pragma: no cover
        raise NotImplementedError


def split_options(model: str):
    """'vendor/model@think,high' → ('vendor/model', {'think', 'high'})."""
    name, _, opts = model.partition("@")
    return name, {o.strip().lower() for o in opts.split(",") if o.strip()}


@dataclass
class OpenAICompatibleClient(ChatClient):
    """Any /chat/completions API (NVIDIA API Catalog, OpenAI, OpenRouter, …)."""
    api_key: str
    models: Sequence[str]
    base_url: str = "https://integrate.api.nvidia.com/v1"
    timeout: float = 60.0
    retired: set = field(default_factory=set)
    session: requests.Session = field(default_factory=requests.Session)
    provider: str = "openai"
    # Groq counts the requested max_tokens against its per-minute token limit, so ask for no more than needed.
    max_tokens_cap: Optional[int] = None

    def _payload(self, model: str, messages, temperature, max_tokens, json_mode):
        name, opts = split_options(model)
        if self.max_tokens_cap:
            max_tokens = min(max_tokens, self.max_tokens_cap)
        body = {"model": name, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False}
        effort = opts & {"low", "medium", "high"}
        if effort:  # reasoning models (gpt-oss): less reasoning = fewer tokens against the free quota
            body["reasoning_effort"] = effort.pop()
        elif self.provider == "groq" and "gpt-oss" in name:
            body["reasoning_effort"] = "low"  # default for the free quota; '@medium' in a chain entry overrides
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    def _post(self, body) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            timeout=self.timeout,
        )

    def _call_once(self, model, messages, temperature, max_tokens, json_mode) -> Completion:
        body = self._payload(model, messages, temperature, max_tokens, json_mode)
        try:
            r = self._post(body)
            # Some models reject response_format or chat_template_kwargs; retry plainly once.
            if r.status_code in (400, 422) and (json_mode or "chat_template_kwargs" in body or "reasoning_effort" in body):
                body = dict(body)
                body.pop("response_format", None)
                body.pop("chat_template_kwargs", None)
                body.pop("reasoning_effort", None)
                r = self._post(body)
        except requests.exceptions.InvalidHeader:
            raise ProviderError("auth", f"The {self.provider} API key is malformed (it contains spaces or line breaks)", model)
        except requests.Timeout:
            raise ProviderError("timeout", f"{model} did not respond within {int(self.timeout)}s", model)
        except requests.RequestException as e:
            raise ProviderError("network", f"Could not reach the model provider ({type(e).__name__})", model)

        if r.status_code == 200:
            try:
                data = r.json()
                msg = data["choices"][0]["message"]
                text = _THINK_RE.sub("", msg.get("content") or "").strip()
            except (ValueError, KeyError, IndexError, TypeError):
                raise ProviderError("bad_response", "The provider returned an unreadable response", model, 200)
            if not text:
                raise ProviderError("bad_response", "The model returned an empty answer", model, 200)
            usage = data.get("usage") or {}
            quota = {k.lower(): v for k, v in (getattr(r, "headers", None) or {}).items() if k.lower().startswith("x-ratelimit-")}
            return Completion(text=text, model=model, provider=self.provider, quota=quota,
                              prompt_tokens=int(usage.get("prompt_tokens") or 0), completion_tokens=int(usage.get("completion_tokens") or 0))

        detail = _clean_message(r.text)
        if r.status_code in (401, 403):
            raise ProviderError("auth", f"The {self.provider} API key was rejected", model, r.status_code)
        low = detail.lower()
        if r.status_code in (404, 410) or "end of life" in low or (r.status_code == 400 and "not found" in low):
            raise ProviderError("model_unavailable", f"{model} is not available: {detail}", model, r.status_code)
        if r.status_code == 429 or (r.status_code == 413 and "rate limit" in low):
            try:
                retry_after = float((getattr(r, "headers", None) or {}).get("retry-after", ""))
            except (TypeError, ValueError):
                retry_after = None
            scope = "day" if re.search(r"per day|\b(tpd|rpd)\b", low) else "minute" if re.search(r"per minute|\b(tpm|rpm)\b", low) else None
            raise ProviderError("rate_limited", "The provider's free rate limit was hit" + (" for today" if scope == "day" else "")
                                + f" ({detail[:160]})", model, r.status_code, retry_after=retry_after, scope=scope)
        if r.status_code >= 500:
            raise ProviderError("server", f"Provider error {r.status_code}: {detail}", model, r.status_code)
        raise ProviderError("bad_request", f"Provider rejected the request ({r.status_code}): {detail}", model, r.status_code)

    def _complete_sync(self, messages, temperature, max_tokens, json_mode) -> Completion:
        self.api_key = (self.api_key or "").strip()
        if not self.api_key or "your-key-here" in self.api_key.lower():
            raise ProviderError("not_configured", f"No API key is configured on the server for {self.provider}")
        last: Optional[ProviderError] = None
        for model in self.models:
            if model in self.retired:
                continue
            for attempt in range(2):
                try:
                    return self._call_once(model, messages, temperature, max_tokens, json_mode)
                except ProviderError as e:
                    last = e
                    if e.kind == "model_unavailable":
                        self.retired.add(model)
                        log.warning("Model %s unavailable, trying next in chain: %s", model, e.message)
                        break
                    if e.kind in ("auth", "not_configured", "bad_request"):
                        raise
                    if e.kind == "rate_limited" and e.scope == "day":
                        break  # nothing to wait for today: let the router try another free model
                    if e.retryable and attempt == 0:
                        wait = 1.0
                        if e.kind == "rate_limited":
                            # A per-minute token limit clears within seconds; waiting is cheaper than failing over.
                            wait = min(e.retry_after, 20.0) + 0.5 if e.retry_after is not None else 2.0
                        time.sleep(wait)
                        continue
                    break  # retryable failure twice: move to the next model
        if last and last.kind == "model_unavailable":
            raise ProviderError("model_unavailable", "None of the configured models are available: " + ", ".join(self.models), last.model, last.status)
        raise last or ProviderError("model_unavailable", "No models configured")

    async def complete(self, messages, *, temperature=0.1, max_tokens=2048, json_mode=False) -> Completion:
        t0 = time.monotonic()
        out = await asyncio.to_thread(self._complete_sync, messages, temperature, max_tokens, json_mode)
        out.seconds = round(time.monotonic() - t0, 2)
        return out


@dataclass
class NvidiaChatClient(OpenAICompatibleClient):
    provider: str = "nvidia"

    def _payload(self, model: str, messages, temperature, max_tokens, json_mode):
        body = super()._payload(model, messages, temperature, max_tokens, json_mode)
        name, opts = split_options(model)
        if "nemotron-3" in name or "nemotron-nano-3" in name:
            # Nemotron 3 models reason by default. Off unless the chain asks for "@think".
            body["chat_template_kwargs"] = {"enable_thinking": "think" in opts}
        if "gpt-oss" in name and "reasoning_effort" not in body:
            # Reasoning tokens count against max_tokens; keep reasoning short so an answer is produced.
            body["reasoning_effort"] = "medium" if "think" in opts else "low"
        return body


def get_client(task: str = "analysis") -> ChatClient:
    from app.llm.router import get_client as _get
    return _get(task)


def set_client(client: Optional[ChatClient], task: Optional[str] = None) -> None:
    """Swap the provider (used by tests). Without a task, applies to every task."""
    from app.llm.router import set_client as _set
    _set(client, task)
