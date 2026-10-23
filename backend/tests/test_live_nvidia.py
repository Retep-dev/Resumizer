"""Live integration test against the real NVIDIA API.

Skipped unless RESUMIZER_LIVE=1 and NVIDIA_API_KEY are set. Asserts accuracy,
not just HTTP 200: the analysis must preserve real roles, invent nothing, and
the coach must hold a grounded multi-turn conversation.
"""
import asyncio
import os
import re


def notice(title, text):
    """Print, and in GitHub Actions also publish as an annotation."""
    print(f"{title}: {text}")
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::notice title={title}::{' '.join(str(text).split())[:900]}")

import pytest

from app.config import settings

pytestmark = pytest.mark.skipif(
    os.getenv("RESUMIZER_LIVE") != "1" or not settings.api_key_configured,
    reason="live test: set RESUMIZER_LIVE=1 and NVIDIA_API_KEY",
)


def test_live_pipeline_is_accurate_and_grounded():
    from app.agents.pipeline import run_resumizer_pipeline
    from tests.conftest import DATA_JD, PRIYA_RESUME

    result = asyncio.run(run_resumizer_pipeline(PRIYA_RESUME, DATA_JD))
    notice("live status", f"{result.status} {({k: (v.status, v.model) for k, v in result.stages.items()})}")
    notice("live warnings", result.warnings)
    assert result.status == "complete", result.stages

    jobs = [(j.job_title, j.company) for j in result.resume_data.work_experience]
    notice("live parsed roles", jobs)
    notice("live score", f"{result.ats_score.overall_score} {[(c.name, c.score) for c in result.ats_score.criteria]} missing={result.ats_score.missing_keywords}")
    assert ("Senior Data Engineer", "Halcyon Freight") in jobs and ("Data Analyst", "Brightwell Insurance") in jobs
    assert result.resume_data.full_name == "Priya Raman"
    assert {"Kafka", "Terraform"} <= set(result.ats_score.missing_keywords)
    assert "Python" in result.ats_score.matched_keywords

    resume_numbers = set(re.findall(r"\d+", PRIYA_RESUME))
    rewrites = [b for e in result.rewrite_report.rewritten_experiences for b in e.rewritten_bullets]
    assert rewrites, "expected AI rewrites"
    for b in rewrites:
        notice("live rewrite", f"[{b.status}] {b.original_bullet} => {b.rewritten_bullet} | ask: {b.needs_confirmation} | {b.note or ''}")
        assert set(re.findall(r"\d+", b.rewritten_bullet)) <= resume_numbers
        assert "Kafka" not in b.rewritten_bullet and "Terraform" not in b.rewritten_bullet
    assert len(result.interview_prep.questions) >= 4
    for q in result.interview_prep.questions:
        notice("live question", f"{q.question_type}: {q.question} | answer: {(q.sample_answer or '')[:300]}")


def test_live_coach_multi_turn():
    from app.agents.career_coach_agent import chat_with_career_coach
    from app.agents.pipeline import run_resumizer_pipeline
    from tests.conftest import DATA_JD, PRIYA_RESUME

    analysis = asyncio.run(run_resumizer_pipeline(PRIYA_RESUME, DATA_JD)).model_dump()
    history = []
    for q in ("What should I fix first for this job?", "Do I have Kafka experience? Answer yes or no first.", "Rewrite my Airflow bullet."):
        reply = asyncio.run(chat_with_career_coach(q, history, PRIYA_RESUME, DATA_JD, analysis))
        notice("live coach turn", f"USER: {q} || COACH: {reply[:700]}")
        assert reply.strip()
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": reply}]
    assert re.match(r"\W*no\b", history[3]["content"].strip(), re.IGNORECASE), "coach must not claim Kafka"
