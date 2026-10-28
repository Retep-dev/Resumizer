"""Rewrites: genuinely better wording, verified against each original bullet."""
import asyncio
import json

import pytest

from app.agents.bullet_facts import extract_facts, verify_rewrite
from app.agents.resume_parser_agent import rule_based_parse
from app.agents.resume_rewrite_agent import NO_CHANGE_NOTE, change_ratio, improvement_score, rewrite_with_ai
from eval.validator_cases import BAD, GOOD
from tests.conftest import DATA_JD, PRIYA_BULLETS, PRIYA_RESUME, FakeClient, good_rewrite_json, proposal_json

RESUME, _ = rule_based_parse(PRIYA_RESUME)
SUPPORTED = ["Python", "SQL", "Airflow", "dbt", "Snowflake"]
MISSING = ["Kafka", "Terraform", "AWS", "Databricks"]
KNOWN = SUPPORTED + ["Tableau", "Git", "React", "Jest", "Figma", "JavaScript", "HTML", "CSS", "WordPress"]
A, Q, M, T, S = PRIYA_BULLETS  # airflow, quality, mentored, tableau, sql


def run(client):
    return asyncio.run(rewrite_with_ai(client, RESUME, PRIYA_RESUME, DATA_JD, SUPPORTED, MISSING))


def by_original(report):
    return {b.original_bullet: b for e in report.rewritten_experiences for b in e.rewritten_bullets}


# ── The validator itself, on hand-written cases ──

@pytest.mark.parametrize("original,rewrite", GOOD)
def test_validator_accepts_honest_improvements(original, rewrite):
    assert verify_rewrite(original, rewrite, missing=MISSING + ["TypeScript"], known_skills=KNOWN) == []


@pytest.mark.parametrize("original,rewrite,why", BAD)
def test_validator_rejects_each_kind_of_fabrication(original, rewrite, why):
    assert verify_rewrite(original, rewrite, missing=MISSING + ["TypeScript"], known_skills=KNOWN), why


def test_merging_another_bullet_is_rejected():
    merged = "Maintain Airflow pipelines that load shipment data into Snowflake, cutting nightly load failures with data quality checks."
    assert any("merged" in p for p in verify_rewrite(A, merged, known_skills=KNOWN, other_bullets=PRIYA_BULLETS))


def test_facts_are_extracted_in_code():
    f = extract_facts(Q, KNOWN)
    assert f.numbers == ["9", "2"] and f.action == "improve" and f.has_result
    f = extract_facts(A, KNOWN)
    assert f.tools == ["Airflow", "Snowflake"] and f.action == "maintain" and not f.has_result


# ── Choosing between candidates ──

def test_best_verified_candidate_wins_and_shows_what_was_checked():
    report, warnings, _ = run(FakeClient(rewrite=good_rewrite_json()))
    q = by_original(report)[Q]
    assert q.status == "rewritten" and q.rewritten_bullet.startswith("Cut nightly load failures from 9 to 2")
    assert any("keeps 9, 2" in c for c in q.checks)
    a = by_original(report)[A]
    # "the" alone is cosmetic; the placeholder version is the real improvement.
    assert a.status == "rewritten" and "[about N GB a day]" in a.rewritten_bullet and "[bracketed]" in a.note
    assert a.needs_confirmation == ["How much shipment data do the pipelines load each day?"]


def test_unsafe_strong_candidate_falls_back_to_safe_one():
    client = FakeClient(rewrite=proposal_json({
        4: ("Built the operations team's weekly claims dashboards in Tableau.",
            "Built weekly Tableau claims dashboards, saving the operations team hours of manual work."),
    }))
    b = by_original(run(client)[0])[T]
    assert b.status == "rewritten" and b.rewritten_bullet == "Built the operations team's weekly claims dashboards in Tableau."


@pytest.mark.parametrize("bad,reason", [
    ("Mentored two junior engineers, boosting team velocity by 35%.", "35%"),
    ("Managed two junior engineers.", "kind of work"),
    ("Mentored two junior engineers in Kafka.", "Kafka"),
    ("Mentored two junior engineers and maintained Airflow pipelines into Snowflake.", "merged"),
])
def test_rewrites_that_change_facts_are_withheld_with_the_reason(bad, reason):
    client = FakeClient(rewrite=[proposal_json({3: (bad, bad)}), proposal_json({3: (bad, bad)})])
    b = by_original(run(client)[0])[M]
    assert b.status == "kept_original" and b.rewritten_bullet == M
    assert b.note.startswith("Rewrite withheld") and reason in b.note
    assert b.needs_confirmation  # always asks for the missing detail instead


def test_retry_targets_only_failed_and_skipped_bullets_and_can_recover():
    first = proposal_json({3: ("Managed two junior engineers.", "Managed two junior engineers.")})
    second = proposal_json({3: ("Mentored two junior engineers.", "Mentored two junior engineers [over N months]."),
                            5: ("Wrote the SQL models behind the pricing team's monthly reporting.",
                                "Wrote the SQL models behind the pricing team's monthly reporting.")})
    client = FakeClient(rewrite=[first, second])
    report, _, _ = run(client)
    assert len(client.calls) == 2
    retry_msg = client.calls[1]["messages"][-1]["content"]
    assert "Bullet 3: your versions were rejected" in retry_msg and "Bullet 5: you skipped it." in retry_msg
    assert by_original(report)[M].status == "rewritten" and by_original(report)[S].status == "rewritten"


def test_cosmetic_or_identical_rewrites_are_not_presented_as_improvements():
    client = FakeClient(rewrite=proposal_json({1: (A, "Maintain the Airflow pipelines that load shipment data into Snowflake.")}))
    b = by_original(run(client)[0])[A]
    assert b.status == "kept_original" and b.note == NO_CHANGE_NOTE and b.needs_confirmation


def test_bullets_the_model_invents_are_ignored_and_order_is_kept():
    client = FakeClient(rewrite=proposal_json({99: ("Led the company IPO.", "Led the company IPO.")}))
    report, _, _ = run(client)
    assert [e.company for e in report.rewritten_experiences] == ["Halcyon Freight", "Brightwell Insurance"]
    assert all(b.original_bullet in PRIYA_BULLETS for b in by_original(report).values())


def test_result_first_reordering_is_scored_as_an_improvement():
    score, why = improvement_score("Rebuilt the newsletter signup form, which doubled weekly signups.",
                                   "Doubled weekly newsletter signups by rebuilding the signup form.", [])
    assert score >= 2 and "leads with the result" in why
    assert change_ratio(A, A) == 0


@pytest.mark.parametrize("summary,ok", [
    ("Data engineer who builds reliable pipelines for logistics and insurance analytics.", False),  # unchanged
    ("Data engineer with 8 years of experience building pipelines.", False),  # years not stated
    ("Data engineer who builds Kafka streaming pipelines.", False),  # missing skill
    ("Data engineer who builds pipelines that boost revenue.", False),  # invented outcome
    ("Data engineer building reliable Airflow and Snowflake pipelines for logistics and insurance analytics.", True),
])
def test_summary_is_checked_like_bullets(summary, ok):
    report, warnings, _ = run(FakeClient(rewrite=proposal_json({}, summary=summary)))
    assert (report.tailored_summary == summary) is ok
    if not ok:
        assert any("summary" in w for w in warnings)


def test_model_nulls_are_tolerated():
    client = FakeClient(rewrite=json.dumps({"bullets": [{"id": 2, "safe": None, "strong": None, "questions": None}], "summary": None}))
    report, _, _ = run(client)
    assert by_original(report)[Q].status == "kept_original"


def test_single_bullet_plain_text_mode_parses_and_verifies():
    from tests.conftest import FakeClient as FC

    def reply(messages):
        bullet = messages[-1]["content"].split("Bullet: ")[1].split("\n")[0]
        if bullet == Q:
            return "SAFE: Cut nightly load failures from 9 to 2 per month by adding data quality checks.\nSTRONG: Cut nightly load failures from 9 to 2 per month by adding data quality checks [to N pipelines].\nQUESTION: How many pipelines?"
        return f"SAFE: {bullet}\nSTRONG: {bullet}\nQUESTION: What changed?"
    client = FC(rewrite=reply)
    report, _, _ = asyncio.run(rewrite_with_ai(client, RESUME, PRIYA_RESUME, DATA_JD, SUPPORTED, MISSING, mode="single"))
    assert len(client.calls) >= 5
    q = by_original(report)[Q]
    assert q.status == "rewritten" and "[to N pipelines]" in q.rewritten_bullet and q.needs_confirmation == ["How many pipelines?"]
    assert by_original(report)[M].status == "kept_original"


@pytest.mark.parametrize("original,rewrite", [
    # Faithful rewrites the first verifier wrongly rejected (found by reviewing round-1 outputs).
    ("Worked with pharmacists to review high-alert medication procedures.", "Reviewed high-alert medication procedures with pharmacists."),
    ("Ran weekly diabetes education sessions for outpatients.", "Conducted weekly diabetes education sessions for outpatients."),
    ("Ran weekly email campaigns in Mailchimp for a list of 18,000 subscribers.", "Executed weekly email campaigns in Mailchimp for 18,000 subscribers."),
    ("Wrote blog posts and product descriptions.", "Authored blog posts and product descriptions."),
])
def test_round1_false_positives_are_accepted(original, rewrite):
    assert verify_rewrite(original, rewrite, known_skills=["Mailchimp"]) == []


@pytest.mark.parametrize("original,rewrite,why", [
    ("Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.",
     "Reduced nightly load failures from nine per month to two per month by adding data quality checks.", "dropped numbers"),
    ("Helped introduce a bedside handover checklist that cut handover time from 45 to 30 minutes.",
     "Introduced a bedside handover checklist that cut handover time from 45 to 30 minutes.", "helped"),
    ("Worked with pharmacists to review high-alert medication procedures.", "Reviewed high-alert medication procedures.", "kind of work"),
    ("Maintain Airflow pipelines that load shipment data into Snowflake.", "Ran Airflow pipelines that load shipment data into Snowflake.", "kind of work"),
])
def test_round1_true_positives_stay_rejected(original, rewrite, why):
    assert any(why in p for p in verify_rewrite(original, rewrite, known_skills=["Airflow", "Snowflake"]))


def test_clean_wording_beats_a_placeholder_version_and_vague_placeholders_are_rejected():
    client = FakeClient(rewrite=proposal_json({
        5: ("Wrote the SQL models behind the pricing team's monthly reporting.",
            "Wrote the SQL models behind the pricing team's monthly reporting [covering N products]."),
        4: ("Built weekly claims dashboards in Tableau for the operations team.",
            "Built weekly claims dashboards in Tableau for the operations team [for which team]."),
    }))
    report, _, _ = run(client)
    s = by_original(report)[S]
    assert s.rewritten_bullet == "Wrote the SQL models behind the pricing team's monthly reporting." and s.needs_confirmation
    t = by_original(report)[T]
    assert t.status == "kept_original"  # safe was identical, strong's placeholder asks for no number
