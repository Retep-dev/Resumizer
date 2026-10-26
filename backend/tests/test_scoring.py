"""5–6: relevant skill gaps from the posting, transparent and consistent ATS scoring."""
import asyncio
from datetime import date

from app.agents.job_analysis_agent import analyze_job_with_ai, ground_requirements, rule_based_requirements
from app.agents.resume_parser_agent import rule_based_parse
from app.agents.scoring import score_resume
from app.schemas.resume import JobRequirement, JobRequirements
from tests.conftest import DATA_JD, FRONTEND_JD, FRONTEND_RESUME, PRIYA_RESUME, FakeClient, data_jd_json

TODAY = date(2026, 10, 1)


def _reqs():
    reqs, _, _ = asyncio.run(analyze_job_with_ai(FakeClient(job=data_jd_json()), DATA_JD))
    return reqs


def test_job_requirements_are_grounded_in_the_posting():
    reqs = _reqs()
    terms = [r.term for r in reqs.requirements]
    assert "Kafka" in terms and "Terraform" in terms
    hallucinated = JobRequirements(requirements=[JobRequirement(term="Rust"), JobRequirement(term="Kafka")])
    grounded, warnings = ground_requirements(hallucinated, DATA_JD)
    terms = [r.term for r in grounded.requirements]
    assert "Kafka" in terms and "Rust" not in terms  # the rest are backfilled from the posting's own text
    assert any("aren't in the job description" in w for w in warnings)


def test_gaps_are_missing_from_resume_and_matches_are_present():
    resume, _ = rule_based_parse(PRIYA_RESUME)
    ats, gap = score_resume(resume, PRIYA_RESUME, _reqs(), "ai", today=TODAY)
    assert {"Kafka", "Terraform", "AWS"} <= set(gap.missing_hard_skills)
    assert {"Python", "SQL", "Airflow", "dbt", "Snowflake"} <= set(gap.matched_hard_skills)
    # Nothing missing is also claimed as matched, and nothing matched lacks evidence.
    assert not set(ats.matched_keywords) & set(ats.missing_keywords)
    for ev in ats.keyword_evidence:
        if ev.found:
            assert ev.evidence and ev.evidence.split("…")[0][:20] in PRIYA_RESUME
    assert "Databricks" in ats.missing_keywords  # preferred, still reported


def test_recommendations_never_tell_the_candidate_to_claim_missing_skills():
    resume, _ = rule_based_parse(PRIYA_RESUME)
    _, gap = score_resume(resume, PRIYA_RESUME, _reqs(), "ai", today=TODAY)
    assert gap.priority_skill_recommendations
    for r in gap.priority_skill_recommendations:
        if "doesn't mention" in r:
            assert "If you haven't, leave it off" in r


def test_score_is_defined_by_published_criteria():
    resume, _ = rule_based_parse(PRIYA_RESUME)
    ats, _ = score_resume(resume, PRIYA_RESUME, _reqs(), "ai", today=TODAY)
    assert [c.name for c in ats.criteria] == ["Keywords", "Experience", "Formatting"]
    assert abs(sum(c.weight for c in ats.criteria) - 1.0) < 1e-9
    expected = round(sum(c.score * c.weight for c in ats.criteria))
    assert ats.overall_score == expected
    # 5 of 9 required + 0 of 1 preferred: (5)/(9+0.5) → 53
    assert ats.keyword_match_score == round(100 * 5 / 9.5)
    # ~7.6 years dated experience vs 5+ asked → years part capped at 1.0
    assert ats.experience_match_score >= 70
    assert "Overall = 50% keywords" in ats.breakdown_summary
    assert "“Senior Data Engineer”" in ats.criteria[1].detail  # title keeps its original casing


def test_score_is_consistent_across_runs_and_requirement_order():
    resume, _ = rule_based_parse(PRIYA_RESUME)
    reqs = _reqs()
    a, _ = score_resume(resume, PRIYA_RESUME, reqs, "ai", today=TODAY)
    b, _ = score_resume(resume, PRIYA_RESUME, reqs, "ai", today=TODAY)
    shuffled = JobRequirements(title=reqs.title, min_years=reqs.min_years, requirements=list(reversed(reqs.requirements)))
    c, _ = score_resume(resume, PRIYA_RESUME, shuffled, "ai", today=TODAY)
    assert a.model_dump() == b.model_dump()
    assert (a.overall_score, a.keyword_match_score, a.experience_match_score, a.formatting_score) == \
           (c.overall_score, c.keyword_match_score, c.experience_match_score, c.formatting_score)


def test_rule_based_requirements_are_relevant_to_the_posting():
    reqs, warnings = rule_based_requirements(FRONTEND_JD)
    terms = {r.term for r in reqs.requirements}
    assert {"React", "TypeScript", "GraphQL", "Figma", "Git", "CI/CD", "Communication"} <= terms
    assert "Kubernetes" not in terms and "Python" not in terms
    assert next(r for r in reqs.requirements if r.term == "Next.js").importance == "preferred"
    assert reqs.min_years == 3
    resume, _ = rule_based_parse(FRONTEND_RESUME)
    ats, gap = score_resume(resume, FRONTEND_RESUME, reqs, "rule_based", today=TODAY)
    assert "TypeScript" in gap.missing_hard_skills and "React" in gap.matched_hard_skills
    assert ats.method == "rule_based" and warnings


def test_multiword_terms_need_their_words_together():
    from app.services.text_utils import term_in_text
    jd = "Turn usage data into roadmap decisions; experience with retention modeling and cohort analysis."
    assert not term_in_text("Data modeling", jd)
    assert term_in_text("retention modeling", jd)
    assert term_in_text("A/B testing", "Ran A/B tests on the pricing page.")
    assert term_in_text("stakeholder communication", "Strong communication with stakeholders")
    assert not term_in_text("Go", "Worked at Google")


def test_requirement_terms_are_cleaned_of_qualifiers_and_durations():
    from app.agents.job_analysis_agent import clean_term
    assert clean_term("Strong stakeholder communication") == "Stakeholder communication"
    assert clean_term("Expert knowledge of Python") == "Python"
    assert clean_term("5+ years of experience in data engineering") == ""
    reqs = JobRequirements(requirements=[JobRequirement(term="5+ years of experience in data engineering"),
                                         JobRequirement(term="Strong stakeholder communication", category="soft")])
    grounded, _ = ground_requirements(reqs, DATA_JD)
    terms = [r.term for r in grounded.requirements]
    assert terms[0] == "Stakeholder communication" and not any("year" in t.lower() for t in terms)


def test_either_or_requirements_are_satisfied_by_one_alternative_and_missed_skills_backfilled():
    from app.agents.job_analysis_agent import ground_requirements
    from app.agents.resume_parser_agent import rule_based_parse
    from app.agents.scoring import score_resume
    from app.schemas.resume import JobRequirement, JobRequirements
    from tests.conftest import DATA_JD, PRIYA_RESUME
    terms = ["Python", "SQL", "Airflow", "dbt", "Snowflake", "BigQuery", "Kafka", "Terraform", "AWS"]
    ai = JobRequirements(title="Senior Data Engineer", min_years=5, requirements=[JobRequirement(term=t, category="hard", importance="required") for t in terms])
    reqs, warnings = ground_requirements(ai, DATA_JD)
    names = [r.term for r in reqs.requirements]
    assert "Snowflake or BigQuery" in names and "BigQuery" not in names
    assert ("Databricks", "preferred") in [(r.term, r.importance) for r in reqs.requirements]
    assert any("Databricks" in w for w in warnings)
    resume, _ = rule_based_parse(PRIYA_RESUME)
    ats, _ = score_resume(resume, PRIYA_RESUME, reqs, "ai")
    assert "Snowflake or BigQuery" in ats.matched_keywords and "BigQuery" not in ats.missing_keywords
