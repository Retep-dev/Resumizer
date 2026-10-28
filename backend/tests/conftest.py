import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Union

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import ChatClient, Completion, ProviderError  # noqa: E402
from app.services import session_store  # noqa: E402

# ───────────── Synthetic resumes & postings (fictional people and companies) ─────────────

PRIYA_RESUME = """Priya Raman
Manchester, UK | priya.raman@example.org | +44 7700 900123

SUMMARY
Data engineer who builds reliable pipelines for logistics and insurance analytics.

EXPERIENCE
Senior Data Engineer - Halcyon Freight (Mar 2021 - Present)
• Maintain Airflow pipelines that load shipment data into Snowflake.
• Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.
• Mentored two junior engineers.

Data Analyst - Brightwell Insurance (Jul 2018 - Feb 2021)
• Built weekly claims dashboards in Tableau for the operations team.
• Wrote SQL models that the pricing team used for monthly reporting.

EDUCATION
BSc Mathematics, University of Leeds, 2018

SKILLS
Python, SQL, Airflow, Snowflake, Tableau, dbt, Git
"""

DATA_JD = """Senior Data Engineer - Lumen Logistics (Remote)

We are looking for a data engineer to own our analytics platform.

Requirements
- 5+ years of experience in data engineering
- Expert Python and SQL
- Airflow and dbt for orchestration and modelling
- Snowflake or BigQuery
- Kafka for streaming data
- Terraform and AWS
- Strong stakeholder communication

Nice to have
- Experience with Databricks is a plus
"""

FRONTEND_RESUME = """Tomas Okafor
Lagos, Nigeria | tomas.okafor@example.com

PROFESSIONAL EXPERIENCE
Frontend Developer, Kitebird - Lagos (Jan 2022 - Present)
- Built React components for the checkout flow.
- Worked with designers in Figma to ship a new onboarding screen.

Junior Web Developer, Palmline Media (Jun 2020 - Dec 2021)
- Maintained the company WordPress site and fixed CSS bugs.

EDUCATION
BSc Computer Science, University of Lagos, 2020

SKILLS
JavaScript, React, HTML, CSS, Figma, Git
"""

FRONTEND_JD = """Frontend Engineer
3+ years of experience building web apps with React and TypeScript.
You will write unit tests, work with GraphQL APIs and collaborate with designers in Figma.
Next.js experience is a plus. Strong communication skills required. We use Git and CI/CD."""


def priya_parse_json(**overrides) -> str:
    data = {
        "full_name": "Priya Raman",
        "email": "priya.raman@example.org",
        "phone": "+44 7700 900123",
        "location": "Manchester, UK",
        "summary": "Data engineer who builds reliable pipelines for logistics and insurance analytics.",
        "technical_skills": ["Python", "SQL", "dbt"],
        "tools_and_frameworks": ["Airflow", "Snowflake", "Tableau", "Git"],
        "soft_skills": ["Mentoring"],
        "work_experience": [
            {"company": "Halcyon Freight", "job_title": "Senior Data Engineer", "start_date": "Mar 2021", "end_date": "Present",
             "bullet_points": ["Maintain Airflow pipelines that load shipment data into Snowflake.",
                               "Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.",
                               "Mentored two junior engineers."]},
            {"company": "Brightwell Insurance", "job_title": "Data Analyst", "start_date": "Jul 2018", "end_date": "Feb 2021",
             "bullet_points": ["Built weekly claims dashboards in Tableau for the operations team.",
                               "Wrote SQL models that the pricing team used for monthly reporting."]},
        ],
        "education": [{"institution": "University of Leeds", "degree": "BSc Mathematics", "graduation_year": "2018"}],
        "certifications": [], "projects": [],
    }
    data.update(overrides)
    return json.dumps(data)


def data_jd_json() -> str:
    return json.dumps({
        "title": "Senior Data Engineer", "min_years": 5,
        "requirements": [
            {"term": "Python", "category": "hard", "importance": "required", "aliases": []},
            {"term": "SQL", "category": "hard", "importance": "required", "aliases": []},
            {"term": "Airflow", "category": "hard", "importance": "required", "aliases": []},
            {"term": "dbt", "category": "hard", "importance": "required", "aliases": []},
            {"term": "Snowflake", "category": "hard", "importance": "required", "aliases": ["BigQuery"]},
            {"term": "Kafka", "category": "hard", "importance": "required", "aliases": []},
            {"term": "Terraform", "category": "hard", "importance": "required", "aliases": []},
            {"term": "AWS", "category": "hard", "importance": "required", "aliases": ["Amazon Web Services"]},
            {"term": "stakeholder communication", "category": "soft", "importance": "required", "aliases": []},
            {"term": "Databricks", "category": "hard", "importance": "preferred", "aliases": []},
        ],
    })


# Bullet ids follow resume order: 1-3 Halcyon Freight, 4-5 Brightwell Insurance.
PRIYA_BULLETS = [
    "Maintain Airflow pipelines that load shipment data into Snowflake.",
    "Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.",
    "Mentored two junior engineers.",
    "Built weekly claims dashboards in Tableau for the operations team.",
    "Wrote SQL models that the pricing team used for monthly reporting.",
]


def proposal_json(bullets=None, summary=None) -> str:
    """bullets: {id: (safe, strong)} or {id: (safe, strong, [questions])}."""
    out = []
    for i, v in (bullets or {}).items():
        safe, strong = v[0], v[1]
        out.append({"id": i, "safe": safe, "strong": strong, "questions": list(v[2]) if len(v) > 2 else []})
    return json.dumps({"bullets": out, "summary": summary})


def good_rewrite_json() -> str:
    return proposal_json({
        1: ("Maintain the Airflow pipelines that load shipment data into Snowflake.",
            "Maintain the Airflow pipelines that load shipment data into Snowflake [about N GB a day].",
            ["How much shipment data do the pipelines load each day?"]),
        2: ("Cut nightly load failures from 9 to 2 per month by adding data quality checks.",
            "Cut nightly load failures from 9 to 2 per month by adding data quality checks to the pipelines."),
    }, summary="Data engineer who builds reliable Airflow and Snowflake pipelines for logistics and insurance analytics.")


def interview_json(answer_extra: str = "") -> str:
    qs = []
    for t in ("behavioral", "behavioral", "technical", "technical", "gap_focused", "gap_focused"):
        qs.append({"question_type": t, "question": f"A {t} question about Airflow?", "context_or_reason": "From the posting.",
                   "star_guide": "Use the Halcyon Freight role.",
                   "sample_answer": "At Halcyon Freight I maintain Airflow pipelines into Snowflake. [describe the scale]" + answer_extra})
    return json.dumps({"questions": qs})


# ───────────── Fake provider ─────────────

Handler = Union[str, Exception, Callable[[List[Dict[str, str]]], str]]


class FakeClient(ChatClient):
    """Routes each call by a phrase in the system prompt to a scripted reply."""

    ROUTES = {
        "extract facts from a resume": "parse",
        "read a job description": "job",
        "expert resume editor": "rewrite",
        "hiring manager preparing": "interview",
        "career coach": "coach",
    }

    def __init__(self, **handlers: Union[Handler, List[Handler]]):
        self.handlers = {k: (v if isinstance(v, list) else [v]) for k, v in handlers.items()}
        self.calls: List[Dict] = []

    def route(self, messages) -> str:
        system = messages[0]["content"].lower()
        for phrase, name in self.ROUTES.items():
            if phrase in system:
                return name
        raise AssertionError("unrouted prompt")

    async def complete(self, messages, *, temperature=0.1, max_tokens=2048, json_mode=False) -> Completion:
        name = self.route(messages)
        self.calls.append({"stage": name, "messages": messages})
        queue = self.handlers.get(name)
        if not queue:
            raise ProviderError("model_unavailable", f"no handler for {name}", "fake/model")
        h = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(h, Exception):
            raise h
        text = h(messages) if callable(h) else h
        return Completion(text=text, model="fake/model")


def retired() -> ProviderError:
    return ProviderError("model_unavailable",
                         "meta/llama-3.1-8b-instruct is not available: [410] Gone. The model has reached its end of life",
                         "meta/llama-3.1-8b-instruct", 410)


def healthy_client(**overrides) -> FakeClient:
    handlers = dict(parse=priya_parse_json(), job=data_jd_json(), rewrite=good_rewrite_json(),
                    interview=interview_json(), coach="Focus on Kafka first.")
    handlers.update(overrides)
    return FakeClient(**handlers)


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_store.clear_sessions()
    yield
    session_store.clear_sessions()
