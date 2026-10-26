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


def test_identical_rewrites_are_labelled_and_skipped_bullets_are_requested_again():
    copy = json.dumps({"tailored_summary": None, "rewritten_experiences": [{"company": "Halcyon Freight", "job_title": "Senior Data Engineer",
        "rewritten_bullets": [{"original_bullet": "Mentored two junior engineers.", "rewritten_bullet": "Mentored two junior engineers.",
                               "star_action": "", "star_result": "", "added_keywords": [], "needs_confirmation": []}]}]})
    second = json.dumps({"tailored_summary": None, "rewritten_experiences": [{"company": "Brightwell Insurance", "job_title": "Data Analyst",
        "rewritten_bullets": [{"original_bullet": "Built weekly claims dashboards in Tableau for the operations team.",
                               "rewritten_bullet": "Built and maintained weekly Tableau claims dashboards for the operations team.",
                               "star_action": "", "star_result": "", "added_keywords": [], "needs_confirmation": []}]}]})
    client = FakeClient(rewrite=[copy, second])
    report, warnings, _ = run(client)
    b = _bullets(report)
    assert b["Mentored two junior engineers."].status == "kept_original"
    assert "No stronger wording" in b["Mentored two junior engineers."].note
    assert b["Built weekly claims dashboards in Tableau for the operations team."].status == "rewritten"
    assert len(client.calls) == 2 and "You didn't rewrite these bullets" in client.calls[1]["messages"][-1]["content"]
    assert [e.company for e in report.rewritten_experiences] == ["Halcyon Freight", "Brightwell Insurance"]
    assert any("no change" in w for w in warnings)


def test_rewrite_that_attributes_another_resume_skill_to_a_bullet_is_withheld():
    bullet = "Maintain Airflow pipelines that load shipment data into Snowflake."
    bad = _invented(bullet, "Maintain Airflow pipelines that load shipment data into Snowflake using Python and SQL.")
    report, _, _ = run(FakeClient(rewrite=[bad, bad]))
    b = _bullets(report)[bullet]
    assert b.status == "kept_original" and "attributed" in b.note and "Python" in b.note


def test_unchanged_bullets_always_get_follow_up_questions():
    copy = json.dumps({"tailored_summary": None, "rewritten_experiences": [{"company": "Brightwell Insurance", "job_title": "Data Analyst",
        "rewritten_bullets": [{"original_bullet": "Wrote SQL models that the pricing team used for monthly reporting.",
                               "rewritten_bullet": "Wrote SQL models that the pricing team used for monthly reporting.",
                               "star_action": "", "star_result": "", "added_keywords": [], "needs_confirmation": []}]}]})
    report, _, _ = run(FakeClient(rewrite=copy))
    b = _bullets(report)["Wrote SQL models that the pricing team used for monthly reporting."]
    assert b.status == "kept_original" and len(b.needs_confirmation) == 2 and "number" in b.needs_confirmation[0]


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


def test_identical_summary_is_not_presented_as_tailored():
    same = json.dumps({"tailored_summary": "Data engineer who builds reliable pipelines for logistics and insurance analytics.",
                       "rewritten_experiences": []})
    report, warnings, _ = run(FakeClient(rewrite=same))
    assert report.tailored_summary is None and any("didn't suggest a different summary" in w for w in warnings)
