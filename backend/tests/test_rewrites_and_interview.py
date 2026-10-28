"""3: interview answers stay grounded. (Rewrite tests: test_rewrites.py.)"""
import asyncio
import json

from app.agents.interview_generator_agent import interview_with_ai, rule_based_questions
from app.agents.resume_parser_agent import rule_based_parse
from app.schemas.resume import JobRequirements
from app.services.text_utils import unsupported_numbers
from tests.conftest import DATA_JD, PRIYA_RESUME, FakeClient, good_rewrite_json, interview_json

RESUME, _ = rule_based_parse(PRIYA_RESUME)
SUPPORTED = ["Python", "SQL", "Airflow", "dbt", "Snowflake"]
MISSING = ["Kafka", "Terraform", "AWS", "Databricks"]


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


def test_short_interview_reply_is_retried_then_topped_up_with_labelled_templates():
    one = json.dumps({"questions": [{"question_type": "behavioral", "question": "Tell us about Halcyon Freight.",
                                     "context_or_reason": "", "star_guide": "", "sample_answer": None}]})
    reqs = JobRequirements(title="Senior Data Engineer", min_years=5)
    client = FakeClient(interview=[one, one])
    report, warnings, _ = asyncio.run(interview_with_ai(client, RESUME, PRIYA_RESUME, reqs, SUPPORTED, MISSING))
    assert len(client.calls) == 2
    assert len(report.questions) >= 4
    assert {"technical", "gap_focused"} <= {q.question_type for q in report.questions}
    assert all(q.sample_answer is None for q in report.questions[1:])
    assert any("template question" in w for w in warnings)


def test_interview_answers_inventing_technical_details_are_repaired_or_removed():
    from app.agents.interview_generator_agent import unsupported_specifics
    invented = "I used Snowflake's MERGE statement on a shipment_id key and set `trigger_rule=one_success` in Airflow."
    assert {"MERGE", "shipment_id", "trigger_rule=one_success"} <= unsupported_specifics(invented, PRIYA_RESUME)
    assert not unsupported_specifics("I maintain Airflow pipelines into Snowflake [how you did it]; I haven't used Kafka.",
                                     PRIYA_RESUME + "\nHave you used Kafka?")
    reqs = JobRequirements(title="Senior Data Engineer", min_years=5)
    bad = interview_json(" " + invented)
    q0 = json.loads(bad)["questions"][0]["question"]
    fixed = json.dumps({"answers": [{"question": q0, "sample_answer": "At Halcyon Freight I maintain Airflow pipelines that load shipment data into Snowflake [how you made loads reliable]."}]})
    report, warnings, _ = asyncio.run(interview_with_ai(FakeClient(interview=[bad, fixed]), RESUME, PRIYA_RESUME, reqs, SUPPORTED, MISSING))
    answers = [q.sample_answer for q in report.questions]
    # The fixture's two behavioural questions share text, so both are repaired; the rest stay removed.
    assert all(a and "[how you made loads reliable]" in a for a in answers[:2])
    assert all(a is None for a in answers[2:]) and "technical details" in warnings[0]