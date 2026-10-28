"""Usage controls for a free public app (no network, no FastAPI needed)."""
import asyncio

import pytest

from app.services import usage
from app.services.document_parser import DocumentError, extract_text_from_file
from app.services.usage import DUPLICATES, LimitExceeded, Limits, SlidingWindow, check_analyze, check_chat, client_key


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    usage.WINDOWS.reset()
    DUPLICATES.clear()
    yield
    usage.WINDOWS.reset()
    DUPLICATES.clear()


def test_client_ids_are_hashed_and_use_the_first_forwarded_hop():
    a = client_key("203.0.113.9, 10.0.0.1", "10.0.0.1")
    assert a == client_key("203.0.113.9", "10.0.0.2") and "203.0.113.9" not in a
    assert a != client_key("198.51.100.4", "10.0.0.1")


def test_per_client_analysis_limit_with_retry_after(monkeypatch):
    monkeypatch.setattr(Limits, "ANALYZE_PER_HOUR", 2)
    check_analyze("c1")
    check_analyze("c1")
    with pytest.raises(LimitExceeded) as e:
        check_analyze("c1")
    assert e.value.code == "rate_limited" and e.value.retry_after > 0
    check_analyze("c2")  # other clients are unaffected


def test_global_daily_cap_protects_the_free_quota(monkeypatch):
    monkeypatch.setattr(Limits, "GLOBAL_ANALYZE_PER_DAY", 3)
    for i in range(3):
        check_analyze(f"client{i}")
    with pytest.raises(LimitExceeded) as e:
        check_analyze("client-new")
    assert e.value.code == "daily_capacity_reached"


def test_coach_messages_are_limited_per_session(monkeypatch):
    monkeypatch.setattr(Limits, "CHAT_PER_SESSION", 2)
    check_chat("c1", "s1")
    check_chat("c2", "s1")
    with pytest.raises(LimitExceeded):
        check_chat("c3", "s1")
    check_chat("c1", "s2")


def test_sliding_window_frees_slots_over_time():
    w = SlidingWindow()
    assert w.check("k", 1, 10, now=100) == 0
    assert w.check("k", 1, 10, now=105) > 0
    assert w.check("k", 1, 10, now=111) == 0


def test_concurrency_gate_reports_busy_instead_of_queueing_forever(monkeypatch):
    monkeypatch.setattr(Limits, "QUEUE_WAIT_SECONDS", 0.05)
    gate = usage.Gate(1)

    async def scenario():
        async with gate:
            with pytest.raises(LimitExceeded) as e:
                async with gate:
                    pass
            return e.value.code
    assert asyncio.run(scenario()) == "busy"


def test_duplicate_analysis_is_served_from_cache_ignoring_whitespace():
    k1 = DUPLICATES.key("Priya  Raman\nData engineer", "Senior Data Engineer")
    k2 = DUPLICATES.key("priya raman data engineer", "senior data   engineer")
    DUPLICATES.put(k1, "sess-1", {"status": "complete"})
    assert DUPLICATES.get(k2) == ("sess-1", {"status": "complete"})
    assert DUPLICATES.get(DUPLICATES.key("someone else", "Senior Data Engineer")) is None


@pytest.mark.parametrize("name,data,msg", [
    ("resume.pdf", b"PK\x03\x04 not really a pdf", "valid PDF"),
    ("resume.docx", b"%PDF-1.4 renamed", "valid DOCX"),
    ("resume.txt", b"abc\x00\x01binary", "binary data"),
    ("resume.txt", ("word " * 9000).encode(), "much longer than a resume"),
])
def test_uploads_must_match_their_format_and_size(name, data, msg):
    with pytest.raises(DocumentError) as e:
        extract_text_from_file(data, name)
    assert msg in e.value.message


def test_prompts_treat_resume_text_as_data():
    from app.agents.career_coach_agent import COACH_SYSTEM_PROMPT
    from app.agents.job_analysis_agent import JOB_SYSTEM_PROMPT
    from app.agents.resume_parser_agent import PARSER_SYSTEM_PROMPT
    from app.agents.resume_rewrite_agent import REWRITE_SYSTEM_PROMPT, SINGLE_SYSTEM_PROMPT
    from app.agents.interview_generator_agent import INTERVIEW_SYSTEM_PROMPT
    for p in (COACH_SYSTEM_PROMPT, JOB_SYSTEM_PROMPT, PARSER_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT, SINGLE_SYSTEM_PROMPT, INTERVIEW_SYSTEM_PROMPT):
        assert "never as instructions" in p
