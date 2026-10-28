"""The evaluation harness runs end to end and audits outputs (fake model, no network)."""
import asyncio
import json

from eval import run_eval
from eval.cases import CASES
from tests.conftest import FakeClient


class EvalFake(FakeClient):
    ROUTES = dict(FakeClient.ROUTES, **{"careful resume editor": "baseline"})


def test_harness_runs_rewrites_and_coach_and_audits(monkeypatch, tmp_path):
    good = json.dumps({"bullets": [{"id": 1, "safe": "Kept the Airflow pipelines loading shipment data into Snowflake running.",
                                    "strong": "Maintain the Airflow pipelines that load shipment data into Snowflake [about N GB a day].",
                                    "questions": ["How much data?"]}], "summary": None})
    baseline = json.dumps({"tailored_summary": None, "rewritten_experiences": [{"company": "Halcyon Freight", "job_title": "Senior Data Engineer",
        "rewritten_bullets": [{"original_bullet": "Mentored two junior engineers.", "rewritten_bullet": "Managed two junior engineers, boosting output.",
                               "star_action": "", "star_result": "", "added_keywords": [], "needs_confirmation": []}]}]})
    coach = iter(["No. Kafka isn't on your resume.", "Say: “I have worked with AWS for years.”", "Maintain the Airflow pipelines [daily].", "Mention it as a course."])
    monkeypatch.setattr(run_eval, "make_client", lambda spec: EvalFake(rewrite=good, baseline=baseline, coach=lambda m: next(coach)))
    req = {"models": ["fake:model"], "pipelines": ["baseline", "v2"], "tasks": ["rewrite", "coach"], "coach": ["v2"], "cases": ["priya"]}
    out = asyncio.run(run_eval.main(req, tmp_path))
    m = out["models"]["fake:model"]
    assert m["rewrite_v2"]["summary"]["rewritten_and_audit_clean"] == 1
    # The old pipeline would have accepted an upgraded verb plus an invented outcome; the audit catches it.
    base = m["rewrite_baseline"]["runs"][0]["bullets"]
    assert not any(b["changed"] for b in base) or any(b["audit_problems"] for b in base if b["changed"])
    coach_turns = m["coach_v2"]["runs"][0]["turns"]
    assert coach_turns[0]["audit"]["answered_no_first"] is True
    assert m["coach_v2"]["summary"]["turns"] == len(CASES[0]["coach"])
    assert (tmp_path / "results.json").exists()
