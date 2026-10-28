"""HTTP layer: status codes, error codes and the chat contract. Needs FastAPI + httpx."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.llm import set_client  # noqa: E402
from app.main import app  # noqa: E402
from tests.conftest import DATA_JD, PRIYA_RESUME, FakeClient, healthy_client, retired  # noqa: E402

api = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_limits():
    from app.services import usage
    usage.WINDOWS.reset()
    usage.DUPLICATES.clear()
    yield
    usage.WINDOWS.reset()
    usage.DUPLICATES.clear()


@pytest.fixture
def ai(request):
    client = getattr(request, "param", None) or healthy_client()
    set_client(client)
    yield client
    set_client(None)


def analyze(name="cv.txt", body=PRIYA_RESUME.encode(), jd=DATA_JD):
    return api.post("/api/v1/analyze", files={"file": (name, body, "text/plain")}, data={"job_description": jd})


def test_analyze_returns_grounded_complete_result(ai):
    r = analyze()
    assert r.status_code == 200
    body = r.json()
    assert body["analysis"]["status"] == "complete"
    assert body["analysis"]["resume_data"]["work_experience"][0]["company"] == "Halcyon Freight"


@pytest.mark.parametrize("kwargs,status,code", [
    (dict(name="cv.doc"), 400, "validation_failed"),
    (dict(name="cv.png"), 400, "validation_failed"),
    (dict(jd="too short"), 400, "validation_failed"),
    (dict(body=b""), 400, "validation_failed"),
    (dict(body=b"tiny resume"), 422, "parsing_failed"),
])
def test_validation_and_parsing_errors_are_not_500s(ai, kwargs, status, code):
    r = analyze(**kwargs)
    assert r.status_code == status
    assert r.json()["detail"]["code"] == code


@pytest.mark.parametrize("ai", [FakeClient(parse=retired(), job=retired())], indirect=True)
def test_ai_down_returns_labelled_rule_based_result(ai):
    r = analyze()
    assert r.status_code == 200
    a = r.json()["analysis"]
    assert a["status"] == "unavailable" and a["stages"]["rewrite"]["status"] == "unavailable"


@pytest.mark.parametrize("ai", [FakeClient(parse=retired(), job=retired())], indirect=True)
def test_ai_down_and_unreadable_resume_returns_503(ai):
    r = analyze(body=("lorem ipsum dolor sit amet " * 20).encode())
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_unavailable"


def test_chat_multi_turn_over_http(ai):
    session = analyze().json()["session_id"]
    history = []
    for q in ("What should I fix first?", "And then?"):
        r = api.post("/api/v1/chat", json={"session_id": session, "message": q, "chat_history": history})
        assert r.status_code == 200 and r.json()["grounded_on"] == "session"
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": r.json()["reply"]}]
    assert ai.calls[-1]["messages"][1]["content"] == "What should I fix first?"


def test_chat_expired_session_without_context_is_404(ai):
    r = api.post("/api/v1/chat", json={"session_id": "nope", "message": "hi"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "session_expired"


def test_chat_uses_client_analysis_when_session_is_gone(ai):
    analysis = analyze().json()["analysis"]
    r = api.post("/api/v1/chat", json={"session_id": "restarted", "message": "hi", "analysis": analysis, "job_description": DATA_JD})
    assert r.status_code == 200 and r.json()["grounded_on"] == "client_analysis"


def test_chat_provider_failure_is_503_not_a_fake_reply(ai):
    session = analyze().json()["session_id"]
    ai.handlers["coach"] = [retired()]
    r = api.post("/api/v1/chat", json={"session_id": session, "message": "hi"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_unavailable"
    assert "reply" not in r.json()


def test_status_endpoint_never_exposes_the_key(ai):
    r = api.get("/api/v1/status")
    assert r.status_code == 200 and "nvapi" not in r.text



def test_repeated_identical_analysis_uses_no_ai_calls(ai):
    first = analyze()
    calls = len(ai.calls)
    second = analyze(body=PRIYA_RESUME.replace("\n", "\n\n").encode())
    assert second.status_code == 200 and second.json()["session_id"] == first.json()["session_id"]
    assert len(ai.calls) == calls


def test_per_client_analysis_limit_returns_429_with_retry_after(ai, monkeypatch):
    from app.services.usage import Limits
    monkeypatch.setattr(Limits, "ANALYZE_PER_HOUR", 1)
    assert analyze().status_code == 200
    r = analyze(body=(PRIYA_RESUME + "\nExtra line so it isn't a duplicate.").encode())
    assert r.status_code == 429 and r.json()["detail"]["code"] == "rate_limited" and int(r.headers["retry-after"]) > 0


def test_oversized_job_description_is_rejected(ai):
    r = analyze(jd="word " * 5000)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "validation_failed"


@pytest.mark.parametrize("ai", [FakeClient(coach=__import__("app.llm", fromlist=["ProviderError"]).ProviderError(
    "rate_limited", "Today's free AI capacity is used up for coach"))], indirect=True)
def test_exhausted_free_quota_is_a_clear_coach_error(ai):
    from tests.conftest import healthy_client
    set_client(healthy_client())
    sid = analyze().json()["session_id"]
    set_client(ai)
    r = api.post("/api/v1/chat", json={"session_id": sid, "message": "What should I fix first?", "chat_history": []})
    assert r.status_code == 429 and r.json()["detail"]["code"] == "ai_quota_exhausted"
    assert "free AI capacity" in r.json()["detail"]["message"]


def test_status_reports_free_only_routing_and_usage(ai):
    body = api.get("/api/v1/status").json()
    assert body["paid_providers"].startswith("none") and "usage" in body
    assert all(row["provider"] in ("nvidia", "groq", "cerebras") for rows in body["tasks"].values() for row in rows)
