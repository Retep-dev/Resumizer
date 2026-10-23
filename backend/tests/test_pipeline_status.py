"""9: transparent processing status and fallbacks that never fabricate."""
import asyncio
import re

import pytest

from app.agents.pipeline import AnalysisUnavailable, run_resumizer_pipeline
from app.llm import AgentOutputError, ProviderError
from tests.conftest import DATA_JD, PRIYA_RESUME, FakeClient, healthy_client, retired


def run(client, resume=PRIYA_RESUME, jd=DATA_JD):
    return asyncio.run(run_resumizer_pipeline(resume, jd, client=client))


def test_healthy_ai_gives_complete_status_with_models_recorded():
    result = run(healthy_client())
    assert result.status == "complete"
    assert {k: v.status for k, v in result.stages.items()} == {
        "parse": "ai", "job": "ai", "scoring": "rule_based", "rewrite": "ai", "interview": "ai"}
    assert result.stages["parse"].model == "fake/model"
    assert result.ats_score.method == "ai"
    assert [j.company for j in result.resume_data.work_experience] == ["Halcyon Freight", "Brightwell Insurance"]


def test_retired_model_everywhere_is_reported_as_unavailable_not_success():
    client = FakeClient(parse=retired(), job=retired(), rewrite=retired(), interview=retired())
    result = run(client)
    assert result.status == "unavailable"
    assert result.stages["parse"].status == "rule_based"
    assert result.stages["job"].status == "rule_based"
    assert result.stages["rewrite"].status == "unavailable"
    assert result.stages["interview"].status == "rule_based"
    assert "isn't available" in result.stages["parse"].message
    # Rewrites are withheld rather than faked, and later AI stages weren't even attempted.
    assert result.rewrite_report.rewritten_experiences == [] and result.rewrite_report.tailored_summary is None
    assert [c["stage"] for c in client.calls].count("rewrite") == 0
    assert result.warnings


def test_fallback_output_contains_nothing_invented():
    result = run(FakeClient(parse=retired(), job=retired()))
    blob = result.model_dump_json()
    for invented in ("Engineering Experience", "Software Developer", "Cloud Architecture", "CI/CD Automation",
                     "candidate@example.com", "Bachelor of Science in Computer Science", "35%"):
        assert invented not in blob, invented
    resume_numbers = set(re.findall(r"\d+", PRIYA_RESUME))
    for q in result.interview_prep.questions:
        assert q.sample_answer is None
    for b in (b for e in result.rewrite_report.rewritten_experiences for b in e.rewritten_bullets):
        assert set(re.findall(r"\d+", b.rewritten_bullet)) <= resume_numbers
    assert [j.job_title for j in result.resume_data.work_experience] == ["Senior Data Engineer", "Data Analyst"]


def test_one_failed_stage_gives_partial_status():
    result = run(healthy_client(rewrite=AgentOutputError("garbled")))
    assert result.status == "partial"
    assert result.stages["rewrite"].status == "unavailable"
    assert result.stages["interview"].status == "ai"


def test_transient_failure_in_parse_still_lets_later_ai_stages_run():
    client = healthy_client(parse=ProviderError("timeout", "slow", "m"))
    result = run(client)
    assert result.stages["parse"].status == "rule_based"
    assert result.stages["rewrite"].status == "ai"
    assert result.status == "partial"


def test_unreadable_resume_with_ai_down_fails_transparently():
    with pytest.raises(AnalysisUnavailable) as e:
        run(FakeClient(parse=retired(), job=retired()), resume="lorem ipsum dolor sit amet " * 20)
    assert "couldn't be read reliably" in e.value.message
    assert e.value.reason["kind"] == "model_unavailable"
