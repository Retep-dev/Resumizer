"""Free-only routing: no paid provider can be called; quotas and unstable models are handled."""
import asyncio
import json

import pytest

from app.llm import router
from app.llm.provider import Completion, ProviderError, split_options
from tests.test_provider import KEY, FakeResponse, FakeSession, ok


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    router._provider_clients.clear()
    router._task_clients.clear()
    router.HEALTH.__init__()
    for t in ("ANALYSIS", "REWRITE", "INTERVIEW", "COACH"):
        monkeypatch.delenv(f"MODELS_{t}", raising=False)
    monkeypatch.delenv("DAILY_REQUEST_CAPS", raising=False)
    monkeypatch.setattr(router.settings, "NVIDIA_API_KEY", KEY)
    yield
    router._provider_clients.clear()
    router._task_clients.clear()
    router.HEALTH.__init__()


def test_default_chain_is_free_for_every_task():
    for task in ("analysis", "rewrite", "interview", "coach"):
        chain = router.settings.task_chain(task)
        assert chain and all(p in router.FREE_PROVIDERS for p, _ in chain)


def test_paid_providers_do_not_exist_and_cannot_be_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_PROVIDERS", "true")
    for name in ("openai", "anthropic", "openrouter", "gemini"):
        usable, why = router.provider_status(name)
        assert not usable and "not a free provider" in why
        with pytest.raises(ProviderError):
            router.provider_client(name)
    assert router.settings.ALLOW_PAID_PROVIDERS is False
    assert set(router.PROVIDERS) == {"nvidia", "groq", "cerebras"}


def test_chain_parses_free_providers_and_options(monkeypatch):
    monkeypatch.setenv("MODELS_REWRITE", "groq:llama-3.3-70b-versatile, nvidia:openai/gpt-oss-20b@think, qwen/qwen3-next")
    assert router.settings.task_chain("rewrite") == [
        ("groq", "llama-3.3-70b-versatile"), ("nvidia", "openai/gpt-oss-20b@think"), ("nvidia", "qwen/qwen3-next")]
    assert split_options("openai/gpt-oss-20b@think") == ("openai/gpt-oss-20b", {"think"})


def test_a_paid_entry_in_a_chain_is_skipped_never_called(monkeypatch):
    monkeypatch.setenv("MODELS_REWRITE", "anthropic:claude-x,nvidia:m1")
    session = FakeSession([ok("from nvidia")])
    router.provider_client("nvidia").session = session
    out = asyncio.run(router.get_client("rewrite").complete([{"role": "user", "content": "hi"}]))
    assert out.text == "from nvidia" and [c["json"]["model"] for c in session.calls] == ["m1"]


def test_groq_without_key_is_skipped_with_a_reason(monkeypatch):
    monkeypatch.setattr(router.settings, "GROQ_API_KEY", "")
    assert router.provider_status("groq") == (False, "off: no GROQ_API_KEY on the server")
    monkeypatch.setattr(router.settings, "GROQ_API_KEY", "gsk_test")
    assert router.provider_status("groq") == (True, "ready")
    c = router.provider_client("groq")
    assert c.base_url == "https://api.groq.com/openai/v1" and c.provider == "groq"


def test_daily_cap_keeps_usage_inside_the_free_quota(monkeypatch):
    monkeypatch.setenv("DAILY_REQUEST_CAPS", "nvidia:m1:2")
    session = FakeSession([ok("a"), ok("b")])
    router.provider_client("nvidia").session = session
    chain = router.ChainClient(task="coach", entries=[("nvidia", "m1")])
    for _ in range(2):
        asyncio.run(chain.complete([{"role": "user", "content": "x"}]))
    with pytest.raises(ProviderError) as e:
        asyncio.run(chain.complete([{"role": "user", "content": "x"}]))
    assert e.value.kind == "rate_limited" and "free AI capacity" in e.value.message and len(session.calls) == 2


def test_model_that_keeps_failing_is_cooled_down(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    empty = FakeResponse(200, {"choices": [{"message": {"content": ""}}]})
    session = FakeSession([empty, ok("backup")] * 3)
    router.provider_client("nvidia").session = session
    chain = router.ChainClient(task="rewrite", entries=[("nvidia", "flaky"), ("nvidia", "steady")])
    for _ in range(3):
        assert asyncio.run(chain.complete([{"role": "user", "content": "x"}])).model == "steady"
    # After 3 failures the flaky model is skipped without a call.
    calls_before = len(session.calls)
    session.script = [ok("backup")]
    assert asyncio.run(chain.complete([{"role": "user", "content": "x"}])).model == "steady"
    assert len(session.calls) == calls_before + 1
    assert "nvidia:flaky" in router.HEALTH.snapshot()["cooling_down"]


def test_falls_through_to_next_free_model_on_failure(monkeypatch):
    class Boom:
        retired = set()

        async def complete(self, *a, **k):
            raise ProviderError("timeout", "slow", "x")

    class Good:
        retired = set()

        async def complete(self, *a, **k):
            return Completion(text="ok", model="good")

    monkeypatch.setattr(router, "provider_status", lambda p: (True, "ready"))
    monkeypatch.setattr(router.dataclasses, "replace", lambda c, **kw: c)
    router._provider_clients.update({"groq": Boom(), "nvidia": Good()})
    chain = router.ChainClient(task="coach", entries=[("groq", "a"), ("nvidia", "b")])
    assert asyncio.run(chain.complete([{"role": "user", "content": "x"}])).text == "ok"


def test_parallel_tasks_do_not_share_model_state():
    session = FakeSession([ok("a"), ok("b")])
    router.provider_client("nvidia").session = session
    a = router.ChainClient(task="analysis", entries=[("nvidia", "model-a")])
    b = router.ChainClient(task="rewrite", entries=[("nvidia", "model-b")])

    async def both():
        return await asyncio.gather(a.complete([{"role": "user", "content": "1"}]), b.complete([{"role": "user", "content": "2"}]))
    ra, rb = asyncio.run(both())
    assert ra.model == "model-a" and rb.model == "model-b"


def test_status_shows_terms_and_never_keys(monkeypatch):
    monkeypatch.setattr(router.settings, "GROQ_API_KEY", "gsk_SECRET")
    monkeypatch.setenv("MODELS_COACH", "groq:llama-3.3-70b-versatile,nvidia:m1")
    status = router.routing_status()
    assert status["coach"][0]["ready"] is True and "Zero Data Retention" in status["coach"][0]["terms"]
    assert "evaluation only" in status["coach"][1]["terms"]
    assert "SECRET" not in json.dumps(status) and KEY not in json.dumps(status)


def test_nvidia_think_option_and_usage_are_passed_through():
    from app.llm.provider import NvidiaChatClient
    body = {"choices": [{"message": {"content": "x"}}], "usage": {"prompt_tokens": 120, "completion_tokens": 30}}
    c = NvidiaChatClient(api_key=KEY, models=["nvidia/nemotron-3.5-lightning-30b-a3b@think"], session=FakeSession([FakeResponse(200, body)]))
    out = asyncio.run(c.complete([{"role": "user", "content": "hi"}]))
    assert c.session.calls[0]["json"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert (out.prompt_tokens, out.completion_tokens) == (120, 30)
