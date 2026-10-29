"""7–8: valid AI response parsing; retired / unavailable model handling; key hygiene."""
import asyncio
import json

import pytest
import requests

from app.llm import AgentOutputError, NvidiaChatClient, ProviderError, complete_json, extract_json
from app.schemas.resume import JobRequirements
from tests.conftest import FakeClient

KEY = "nvapi-TESTKEY-should-never-leak-1234567890"


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


class FakeSession:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def ok(content):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


def client(script, models=("old/model", "new/model")):
    return NvidiaChatClient(api_key=KEY, models=list(models), session=FakeSession(script), timeout=5)


def complete(c, **kw):
    return asyncio.run(c.complete([{"role": "user", "content": "hi"}], **kw))


# ── Response parsing ──

@pytest.mark.parametrize("reply", [
    '{"title": "Engineer", "min_years": 3, "requirements": []}',
    'Sure! Here you go:\n```json\n{"title": "Engineer", "min_years": 3, "requirements": []}\n```',
    '<think>let me think</think>{"title": "Engineer", "min_years": 3, "requirements": [], "note": "has } brace"}',
])
def test_extract_json_handles_fences_prose_and_braces_in_strings(reply):
    data = extract_json(reply.replace("<think>let me think</think>", ""))
    assert data["title"] == "Engineer"


def test_complete_json_repairs_once_then_succeeds():
    fc = FakeClient(job=["not json at all", '{"title": "Engineer", "requirements": []}'])
    from app.agents.job_analysis_agent import JOB_SYSTEM_PROMPT
    result, model = asyncio.run(complete_json(fc, JOB_SYSTEM_PROMPT, "jd", JobRequirements))
    assert result.title == "Engineer" and len(fc.calls) == 2
    assert "not valid JSON" in fc.calls[1]["messages"][-1]["content"]


def test_complete_json_gives_up_with_a_typed_error():
    fc = FakeClient(job=['{"requirements": "should be a list"}'])
    from app.agents.job_analysis_agent import JOB_SYSTEM_PROMPT
    with pytest.raises(AgentOutputError):
        asyncio.run(complete_json(fc, JOB_SYSTEM_PROMPT, "jd", JobRequirements))


# ── Provider errors ──

def test_retired_model_falls_through_to_next_model_and_is_remembered():
    retired = FakeResponse(410, {"detail": "The model 'old/model' has reached its end of life on 2026-08-26"})
    c = client([retired, ok("hello"), ok("again")])
    assert complete(c).model == "new/model"
    assert "old/model" in c.retired
    assert complete(c).text == "again"
    assert [call["json"]["model"] for call in c.session.calls] == ["old/model", "new/model", "new/model"]


def test_all_models_retired_raises_model_unavailable():
    gone = FakeResponse(404, {"detail": "Function not found"})
    c = client([gone, gone])
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "model_unavailable"


def test_bad_key_is_not_retried_and_never_leaks():
    c = client([FakeResponse(401, f"Unauthorized: key {KEY} invalid")])
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "auth" and len(c.session.calls) == 1
    assert KEY not in str(e.value) and KEY not in json.dumps(e.value.public())


def test_server_error_message_redacts_keys():
    c = client([FakeResponse(500, f"boom Authorization: Bearer {KEY}")] * 4, models=("m",))
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "server" and KEY not in e.value.message


def test_rate_limit_is_retried(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    c = client([FakeResponse(429, "slow down"), ok("done")], models=("m",))
    assert complete(c).text == "done"


def test_timeout_is_classified(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    c = client([requests.Timeout(), requests.Timeout()], models=("m",))
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "timeout"


def test_missing_key_is_reported_without_calling_provider():
    c = NvidiaChatClient(api_key="", models=["m"], session=FakeSession([]))
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "not_configured"


def test_reasoning_text_is_stripped_and_unsupported_options_dropped():
    c = client([FakeResponse(400, "unknown field chat_template_kwargs"), ok("<think>private</think>Final answer")],
               models=("nvidia/nemotron-3-super-120b-a12b",))
    out = complete(c, json_mode=True)
    assert out.text == "Final answer"
    first, second = c.session.calls
    assert "chat_template_kwargs" in first["json"] and "response_format" in first["json"]
    assert "chat_template_kwargs" not in second["json"] and "response_format" not in second["json"]


def test_key_only_in_authorization_header():
    c = client([ok("x")], models=("m",))
    complete(c)
    call = c.session.calls[0]
    assert call["headers"]["Authorization"] == f"Bearer {KEY}"
    assert KEY not in json.dumps(call["json"])


def test_key_whitespace_is_stripped_before_use():
    c = NvidiaChatClient(api_key=KEY + "\n", models=["m"], session=FakeSession([ok("x")]))
    complete(c)
    assert c.session.calls[0]["headers"]["Authorization"] == f"Bearer {KEY}"


def test_malformed_key_is_reported_as_auth_not_network():
    c = client([requests.exceptions.InvalidHeader("bad header")], models=("m",))
    with pytest.raises(ProviderError) as e:
        complete(c)
    assert e.value.kind == "auth" and "malformed" in e.value.message and len(c.session.calls) == 1


def test_settings_strip_pasted_key(monkeypatch):
    import importlib
    import app.config as cfg
    monkeypatch.setenv("NVIDIA_API_KEY", f'  "{KEY}"\n')
    assert importlib.reload(cfg).settings.NVIDIA_API_KEY == KEY
    monkeypatch.delenv("NVIDIA_API_KEY")
    importlib.reload(cfg)
