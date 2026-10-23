"""3: no fabricated numbers; rewrites keep meaning; interview answers stay grounded."""
import asyncio
import json

from app.agents.interview_generator_agent import interview_with_ai, rule_based_questions
from app.agents.resume_parser_agent import rule_based_parse
from app.agents.resume_rewrite_agent import rewrite_with_ai
from app.schemas.resume import JobRequirements
from app.services.text_utils import unsupported_numbers
from tests.conftest import DATA_JD, PRIYA_RESUME, FakeClient, good_rewrite_json, interview_json

RESUME, _ = rule_based_parse(PRIYA_RESUME)
SUPPORTED = ["Python", "SQL", "Airflow", "dbt", "Snowflake"]
MISSING = ["Kafka", "Terraform", "AWS", "Databricks"]


def run(client):
    return asyncio.run(rewrite_with_ai(client, RESUME, PRIYA_RESUME, DATA_JD, SUPPORTED, MISSING))


def _bullets(report):
    return {b.original_bullet: b for e in report.rewritten_experiences for b in e.rewritten_bullets}


def test_valid_rewrites_are_kept_with_confirmation_questions():
    report, warnings, _ = run(FakeClient(rewrite=good_rewrite_json()))
    b = _bullets(report)["Maintain Airflow pipelines that load shipment data into Snowflake."]
    assert b.status == "rewritten" and b.rewritten_bullet.startswith("Own and maintain")
    assert b.needs_confirmation and set(b.added_keywords) == {"Airflow", "Snowflake"}
    kept_numbers = _bullets(report)["Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks."]
    assert kept_numbers.status == "rewritten" and "9" in kept_numbers.rewritten_bullet
    assert report.tailored_summary and not warnings


def _invented(bullet: str, text: str, keywords=None):
    return json.dumps({"tailored_summary": "Data engineer with 8 years of experience and 40% faster pipelines.",
                       "rewritten_experiences": [{"company": "Halcyon Freight", "job_title": "Senior Data Engineer", "rewritten_bullets": [
                           {"original_bullet": bullet, "rewritten_bullet": text, "star_action": "", "star_result": "Improved by 35%",
                            "added_keywords": keywords or [], "needs_confirmation": []}]}]})


def test_rewrite_that_invents_a_percentage_is_withheld():
    bullet = "Mentored two junior engineers."
    bad = _invented(bullet, "Mentored two junior engineers, boosting team velocity by 35%.")
    report, warnings, _ = run(FakeClient(rewrite=[bad, bad]))  # also fails the retry
    b = _bullets(report)[bullet]
    assert b.status == "kept_original" and b.rewritten_bullet == bullet
    assert "35%" in b.note and b.star_result == ""
    assert report.tailored_summary is None  # summary invented "8 years" and "40%"
    assert any("withheld" in w for w in warnings)


def test_rewrite_that_claims_a_missing_skill_is_withheld():
    bullet = "Maintain Airflow pipelines that load shipment data into Snowflake."
    bad = _invented(bullet, "Maintain Airflow and Kafka streaming pipelines on AWS into Snowflake.", ["Kafka", "AWS"])
    report, _, _ = run(FakeClient(rewrite=[bad, bad]))
    b = _bullets(report)[bullet]
    assert b.status == "kept_original" and "Kafka" in b.note


def test_retry_replaces_a_withheld_rewrite_when_the_model_fixes_it():
    bullet = "Mentored two junior engineers."
    bad = _invented(bullet, "Mentored 4 junior engineers.")
    fixed = _invented(bullet, "Mentored two junior engineers through their first production releases.")
    report, warnings, _ = run(FakeClient(rewrite=[bad, fixed]))
    assert _bullets(report)[bullet].status == "rewritten"
    assert not any("withheld because they added" in w for w in warnings)


def test_rewrites_for_bullets_not_in_resume_are_dropped():
    fake = _invented("Led the company IPO.", "Led the company IPO.")
    report, _, _ = run(FakeClient(rewrite=fake))
    assert "Led the company IPO." not in _bullets(report)


def test_no_rewrite_contains_numbers_absent_from_its_original():
    report, _, _ = run(FakeClient(rewrite=good_rewrite_json()))
    for b in _bullets(report).values():
        assert not unsupported_numbers(b.rewritten_bullet, b.original_bullet)


def test_interview_answers_with_invented_numbers_are_removed():
    reqs = JobRequirements(title="Senior Data Engineer", min_years=5)
    report, warnings, _ = asyncio.run(interview_with_ai(
        FakeClient(interview=interview_json(" This cut costs by 27%.")), RESUME, PRIYA_RESUME, reqs, SUPPORTED, MISSING))
    assert len(report.questions) == 6
    assert all(q.sample_answer is None for q in report.questions)
    assert warnings


def test_interview_answers_without_invented_numbers_are_kept():
    reqs = JobRequirements(title="Senior Data Engineer", min_years=5)
    report, warnings, _ = asyncio.run(interview_with_ai(FakeClient(interview=interview_json()), RESUME, PRIYA_RESUME, reqs, SUPPORTED, MISSING))
    assert all(q.sample_answer for q in report.questions) and not warnings
    assert {q.question_type for q in report.questions} == {"behavioral", "technical", "gap_focused"}


def test_rule_based_questions_have_no_sample_answers_and_use_real_roles():
    report, warnings = rule_based_questions(RESUME, JobRequirements(), SUPPORTED, MISSING)
    assert all(q.sample_answer is None for q in report.questions)
    assert "Senior Data Engineer at Halcyon Freight" in report.questions[0].question
    assert any("Kafka" in q.question for q in report.questions if q.question_type == "gap_focused")
    assert warnings
