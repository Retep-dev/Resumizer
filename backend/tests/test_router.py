"""Per-task model routing: paid providers stay off unless explicitly allowed; keys never leak."""
import asyncio
import json

import pytest

from app.llm import router
from app.llm.provider import AnthropicChatClient, Completion, ProviderError, split_options
from tests.test_provider import KEY, FakeResponse, FakeSession, ok


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    router._provider_clients.clear()
    router._task_clients.clear()
    for t in ("ANALYSIS", "REWRITE", "INTERVIEW", "COACH"):
        monkeypatch.delenv(f"MODELS_{t}", raising=False)
    yield
    router._provider_clients.clear()
    router._task_clients.clear()


def test_default_chain_is_nvidia_for_every_task():
    for task in ("analysis", "rewrite", "interview", "coach"):
        chain = router.settings.task_chain(task)
        assert chain and all(p == "nvidia" for p, _ in chain)
        assert chain[0][1] == router.settings.NVIDIA_MODEL_NAME


def test_task_chains_are_independent_and_parse_providers(monkeypatch):
    monkeypatch.setenv("MODELS_REWRITE", "anthropic:claude-haiku-4-5, nvidia:openai/gpt-oss-20b@think, qwen/qwen3-next")
    assert router.settings.task_chain("rewrite") == [
        ("anthropic", "claude-haiku-4-5"), ("nvidia", "openai/gpt-oss-20b@think"), ("nvidia", "qwen/qwen3-next")]
    assert router.settings.task_chain("coach")[0][0] == "nvidia"
    assert split_options("openai/gpt-oss-20b@think") == ("openai/gpt-oss-20b", {"think"})


def test_paid_providers_are_off_by_default_even_with_a_key(monkeypatch):
    monkeypatch.setattr(router.settings, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(router.settings, "ALLOW_PAID_PROVIDERS", False)
    usable, why = router.provider_status("anthropic")
    assert not usable and "ALLOW_PAID_PROVIDERS" in why
    monkeypatch.setattr(router.settings, "ALLOW_PAID_PROVIDERS", True)
    assert router.provider_status("anthropic") == (True, "ready")
    monkeypatch.setattr(router.settings, "ANTHROPIC_API_KEY", "")
    assert not router.provider_status("anthropic")[0]


def test_chain_skips_disabled_paid_entry_and_uses_nvidia(monkeypatch):
    monkeypatch.setenv("MODELS_REWRITE", "anthropic:claude-haiku-4-5,nvidia:m1")
    monkeypatch.setattr(router.settings, "NVIDIA_API_KEY", KEY)
    monkeypatch.setattr(router.settings, "ALLOW_PAID_PROVIDERS", False)
    session = FakeSession([ok("from nvidia")])
    nv = router.provider_client("nvidia")
    nv.session = session
    out = asyncio.run(router.get_client("rewrite").complete([{"role": "user", "content": "hi"}]))
    assert out.text == "from nvidia" and out.provider == "nvidia"
    assert [c["json"]["model"] for c in session.calls] == ["m1"]


def test_chain_falls_through_to_next_provider_on_failure(monkeypatch):
    class Boom:
        retired = set()

        async def complete(self, *a, **k):
            raise ProviderError("timeout", "slow", "x")

    calls = []

    class Good:
        retired = set()

        async def complete(self, *a, **k):
            calls.append(1)
            return Completion(text="ok", model="good")

    monkeypatch.setattr(router, "provider_status", lambda p: (True, "ready"))
    monkeypatch.setattr(router.dataclasses, "replace", lambda c, **kw: c)
    router._provider_clients.update({"openai": Boom(), "nvidia": Good()})
    chain = router.ChainClient(task="coach", entries=[("openai", "a"), ("nvidia", "b")])
    assert asyncio.run(chain.complete([{"role": "user", "content": "x"}])).text == "ok" and calls == [1]


def test_no_usable_model_is_a_clear_not_configured_error(monkeypatch):
    monkeypatch.setattr(router.settings, "ALLOW_PAID_PROVIDERS", False)
    chain = router.ChainClient(task="rewrite", entries=[("anthropic", "claude-x")])
    with pytest.raises(ProviderError) as e:
        asyncio.run(chain.complete([{"role": "user", "content": "x"}]))
    assert e.value.kind == "not_configured" and "ALLOW_PAID_PROVIDERS" in e.value.message


def test_parallel_tasks_do_not_share_model_state(monkeypatch):
    monkeypatch.setattr(router.settings, "NVIDIA_API_KEY", KEY)
    session = FakeSession([ok("a"), ok("b")])
    router.provider_client("nvidia").session = session
    a = router.ChainClient(task="analysis", entries=[("nvidia", "model-a")])
    b = router.ChainClient(task="rewrite", entries=[("nvidia", "model-b")])

    async def both():
        return await asyncio.gather(a.complete([{"role": "user", "content": "1"}]), b.complete([{"role": "user", "content": "2"}]))
    ra, rb = asyncio.run(both())
    assert ra.model == "model-a" and rb.model == "model-b"
    assert sorted(c["json"]["model"] for c in session.calls) == ["model-a", "model-b"]


def test_status_lists_routing_without_secrets(monkeypatch):
    monkeypatch.setattr(router.settings, "ANTHROPIC_API_KEY", "sk-ant-SECRET")
    monkeypatch.setenv("MODELS_COACH", "anthropic:claude-haiku-4-5")
    status = router.routing_status()
    assert status["coach"][0]["provider"] == "anthropic" and status["coach"][0]["ready"] is False
    assert "SECRET" not in json.dumps(status) and KEY not in json.dumps(status)


def test_nvidia_think_option_and_usage_are_passed_through():
    from app.llm.provider import NvidiaChatClient
    body = {"choices": [{"message": {"content": "x"}}], "usage": {"prompt_tokens": 120, "completion_tokens": 30}}
    c = NvidiaChatClient(api_key=KEY, models=["nvidia/nemotron-3.5-lightning-30b-a3b@think"], session=FakeSession([FakeResponse(200, body)]))
    out = asyncio.run(c.complete([{"role": "user", "content": "hi"}]))
    sent = c.session.calls[0]["json"]
    assert sent["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b" and sent["chat_template_kwargs"] == {"enable_thinking": True}
    assert (out.prompt_tokens, out.completion_tokens) == (120, 30)


def test_anthropic_client_sends_system_separately_and_reads_usage():
    body = {"content": [{"type": "text", "text": "hello"}], "usage": {"input_tokens": 50, "output_tokens": 7}}
    c = AnthropicChatClient(api_key="sk-ant-x", models=["claude-haiku-4-5"], session=FakeSession([FakeResponse(200, body)]))
    out = asyncio.run(c.complete([{"role": "system", "content": "rules"}, {"role": "user", "content": "hi"}], json_mode=True))
    sent = c.session.calls[0]
    assert sent["json"]["system"].startswith("rules") and sent["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert sent["headers"]["x-api-key"] == "sk-ant-x" and "sk-ant-x" not in json.dumps(sent["json"])
    assert out.text == "hello" and (out.prompt_tokens, out.completion_tokens) == (50, 7)
