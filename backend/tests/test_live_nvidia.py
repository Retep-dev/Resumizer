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
        print(f"::notice title={title}::{' '.join(str(text).split())[:3500]}")

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
    notice("live status", f"{result.status} {({k: (v.status, v.model) for k, v in result.stages.items()})} WARNINGS {result.warnings}")
    notice("live parsed", f"name={result.resume_data.full_name!r} roles={jobs} skills={result.resume_data.technical_skills + result.resume_data.tools_and_frameworks} REQUIREMENTS {[(r.term, r.importance) for r in result.job_requirements.requirements]}")
    notice("live score", f"{result.ats_score.overall_score} {[(c.name, c.score) for c in result.ats_score.criteria]} MATCHED {result.ats_score.matched_keywords} MISSING {result.ats_score.missing_keywords}")
    notice("live rewrites", f"SUMMARY: {result.rewrite_report.tailored_summary} || " + " || ".join(
        f"[{b.status}] {b.original_bullet} => {b.rewritten_bullet} (ask: {b.needs_confirmation}) {b.note or ''}" for b in rewrites))
    notice("live questions", " || ".join(f"{q.question_type}: {q.question} ANSWER: {(q.sample_answer or '-')[:260]}" for q in result.interview_prep.questions))

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
    all_bullets = sum(len(j.bullet_points) for j in result.resume_data.work_experience)
    improved = [b for b in rewrites if b.status == "rewritten" and b.rewritten_bullet.strip() != b.original_bullet.strip()]
    check(len(rewrites) == all_bullets, f"only {len(rewrites)} of {all_bullets} bullets covered")
    check(len(improved) >= 1, "no bullet was improved")
    for b in rewrites:
        # Every bullet is either improved or comes with questions for the candidate (or was withheld with a reason).
        check(b in improved or b.needs_confirmation or (b.note or "").startswith("Rewrite withheld"),
              f"unchanged bullet with no questions: {b.original_bullet}")
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
        notice(f"live coach turn {len(history) // 2 + 1}", f"USER: {q} || COACH: {reply[:3000]}")
        assert reply.strip()
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": reply}]
    assert re.match(r"\W*no\b", history[3]["content"].strip(), re.IGNORECASE), "coach must not claim Kafka"


def test_live_rewrite_quality_by_model():
    """Runs only the rewrite stage with each working model and reports the results."""
    from app.agents.resume_parser_agent import rule_based_parse
    from app.agents.resume_rewrite_agent import rewrite_with_ai
    from app.llm.provider import NvidiaChatClient
    from tests.conftest import DATA_JD, PRIYA_RESUME

    resume, _ = rule_based_parse(PRIYA_RESUME)
    supported = ["Python", "SQL", "Airflow", "dbt", "Snowflake"]
    missing = ["Kafka", "Terraform", "AWS", "BigQuery"]
    for model in ("nvidia/nemotron-3.5-lightning-30b-a3b", "openai/gpt-oss-20b"):
        client = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=[model], timeout=120)
        try:
            report, warnings, _ = asyncio.run(rewrite_with_ai(client, resume, PRIYA_RESUME, DATA_JD, supported, missing))
        except Exception as e:  # report, don't fail: this is a comparison
            notice(f"live compare {model}", f"ERROR {type(e).__name__}: {getattr(e, 'message', e)}")
            continue
        bullets = [b for e in report.rewritten_experiences for b in e.rewritten_bullets]
        improved = [b for b in bullets if b.status == "rewritten"]
        notice(f"live compare {model}", f"improved {len(improved)}/{len(bullets)}; warnings {warnings} || " + " || ".join(
            f"[{b.status}] {b.original_bullet} => {b.rewritten_bullet} (ask: {b.needs_confirmation}) {b.note or ''}" for b in bullets))
