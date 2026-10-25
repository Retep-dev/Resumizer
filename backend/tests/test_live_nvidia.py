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
    jobs = [(j.job_title, j.company) for j in result.resume_data.work_experience]
    rewrites = [b for e in result.rewrite_report.rewritten_experiences for b in e.rewritten_bullets]
    resume_numbers = set(re.findall(r"\d+", PRIYA_RESUME))

    # Publish the full output first so failures are diagnosable from the API.
    notice("live status", f"{result.status} {({k: (v.status, v.model) for k, v in result.stages.items()})}")
    notice("live warnings", result.warnings)
    notice("live parsed", f"name={result.resume_data.full_name!r} roles={jobs} skills={result.resume_data.technical_skills + result.resume_data.tools_and_frameworks}")
    notice("live requirements", [(r.term, r.category, r.importance) for r in result.job_requirements.requirements])
    notice("live score", f"{result.ats_score.overall_score} {[(c.name, c.score) for c in result.ats_score.criteria]}")
    notice("live matched", result.ats_score.matched_keywords)
    notice("live missing", result.ats_score.missing_keywords)
    notice("live summary", result.rewrite_report.tailored_summary)
    for b in rewrites:
        notice("live rewrite", f"[{b.status}] {b.original_bullet} => {b.rewritten_bullet} | ask: {b.needs_confirmation} | {b.note or ''}")
    for q in result.interview_prep.questions:
        notice("live question", f"{q.question_type}: {q.question} | answer: {(q.sample_answer or '')[:300]}")

    failures = []
    def check(ok, msg):
        if not ok:
            failures.append(msg)
    check(result.status == "complete", f"status {result.status}")
    check(("Senior Data Engineer", "Halcyon Freight") in jobs and ("Data Analyst", "Brightwell Insurance") in jobs, f"roles {jobs}")
    check(result.resume_data.full_name == "Priya Raman", f"name {result.resume_data.full_name!r}")
    check({"Kafka", "Terraform"} <= set(result.ats_score.missing_keywords), "Kafka/Terraform not reported missing")
    check(any(k.lower() == "python" for k in result.ats_score.matched_keywords), "Python not matched")
    check(not any(re.search(r"\byears?\b", k, re.I) for k in result.ats_score.matched_keywords + result.ats_score.missing_keywords), "duration listed as keyword")
    check(bool(rewrites), "no AI rewrites")
    for b in rewrites:
        check(set(re.findall(r"\d+", b.rewritten_bullet)) <= resume_numbers, f"invented number in: {b.rewritten_bullet}")
        check("Kafka" not in b.rewritten_bullet and "Terraform" not in b.rewritten_bullet, f"missing skill claimed in: {b.rewritten_bullet}")
    check(len(result.interview_prep.questions) >= 4, "too few questions")
    for f in failures:
        notice("live FAILED", f)
    assert not failures, failures


def test_live_coach_multi_turn():
    from app.agents.career_coach_agent import chat_with_career_coach
    from app.agents.pipeline import run_resumizer_pipeline
    from tests.conftest import DATA_JD, PRIYA_RESUME

    analysis = asyncio.run(run_resumizer_pipeline(PRIYA_RESUME, DATA_JD)).model_dump()
    history = []
    for q in ("What should I fix first for this job?", "Do I have Kafka experience? Answer yes or no first.", "Rewrite my Airflow bullet."):
        reply = asyncio.run(chat_with_career_coach(q, history, PRIYA_RESUME, DATA_JD, analysis))
        notice("live coach turn", f"USER: {q} || COACH: {reply[:850]}")
        assert reply.strip()
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": reply}]
    assert re.match(r"\W*no\b", history[3]["content"].strip(), re.IGNORECASE), "coach must not claim Kafka"
