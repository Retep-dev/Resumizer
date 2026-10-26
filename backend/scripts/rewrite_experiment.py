"""Compare rewrite prompt variants against the live model (diagnostic, CI only).

Every variant still goes through the same validator, so a variant can only
'win' by producing more rewrites that pass the no-new-facts checks.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents import resume_rewrite_agent as rw  # noqa: E402
from app.agents.resume_parser_agent import rule_based_parse  # noqa: E402
from app.llm.provider import NvidiaChatClient  # noqa: E402
from app.config import settings  # noqa: E402
from tests.conftest import DATA_JD, FRONTEND_JD, FRONTEND_RESUME, PRIYA_RESUME  # noqa: E402

CURRENT = rw.REWRITE_SYSTEM_PROMPT
MUST = CURRENT + """

Important: almost every bullet can be improved without new facts — tighten it, lead with a stronger verb that keeps the meaning, use the posting's term for what the bullet already describes, or add one [placeholder]. rewritten_bullet should differ from original_bullet unless the bullet is already excellent."""
SHORT = """You rewrite resume bullets so they read stronger for a specific job posting, without adding any fact.

For each bullet:
- Lead with a strong verb that keeps the original meaning ("maintain" stays maintain-level, "helped" never becomes "led").
- Use the posting's wording for things the bullet already describes; tighten wordy phrasing.
- Never add tools, skills, numbers, team sizes, purposes or results the bullet doesn't state, and never merge bullets.
- Where a metric or outcome would help, add ONE placeholder in brackets written with letters, e.g. "[for N users]", "[cutting X hours a week]".
- Put 1-2 questions in needs_confirmation that would let the candidate fill the placeholder or strengthen the bullet.
- added_keywords: posting keywords the original bullet already names. Never use a keyword from the missing list.
- star_action / star_result: restate what the bullet says; empty star_result if it states no result.
- tailored_summary: 1-2 sentences using only facts in the resume, or null.

Return one JSON object:
{"tailored_summary": str|null,
 "rewritten_experiences": [{"company": str, "job_title": str,
   "rewritten_bullets": [{"original_bullet": str, "rewritten_bullet": str, "star_action": str, "star_result": str,
                          "added_keywords": [str], "needs_confirmation": [str]}]}]}
Include every bullet from the resume, with original_bullet copied exactly."""

CASES = [
    ("data", PRIYA_RESUME, DATA_JD, ["Python", "SQL", "Airflow", "dbt", "Snowflake"], ["Kafka", "Terraform", "AWS", "Databricks"]),
    ("frontend", FRONTEND_RESUME, FRONTEND_JD, ["React", "Figma"], ["TypeScript", "Next.js", "GraphQL"]),
]


def note(title, text):
    print(f"{title}: {text}")
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::notice title={title}::{' '.join(str(text).split())[:3800]}")


async def main():
    client = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=["nvidia/nemotron-3.5-lightning-30b-a3b"], timeout=90)
    for name, prompt in (("current", CURRENT), ("must-differ", MUST), ("short", SHORT)):
        rw.REWRITE_SYSTEM_PROMPT = prompt
        for case, resume_text, jd, supported, missing in CASES:
            resume, _ = rule_based_parse(resume_text)
            try:
                report, warnings, _ = await rw.rewrite_with_ai(client, resume, resume_text, jd, supported, missing)
            except Exception as e:
                note(f"exp {name}/{case}", f"ERROR {type(e).__name__}: {getattr(e, 'message', e)}")
                continue
            bullets = [b for e in report.rewritten_experiences for b in e.rewritten_bullets]
            improved = [b for b in bullets if b.status == "rewritten"]
            withheld = [b for b in bullets if (b.note or "").startswith("Rewrite withheld")]
            note(f"exp {name}/{case}", f"improved {len(improved)}/{len(bullets)} withheld {len(withheld)} || "
                 + " || ".join(f"[{b.status}] {b.original_bullet} => {b.rewritten_bullet} {('(' + b.note + ')') if b.note and b.status != 'rewritten' else ''}" for b in bullets))


if __name__ == "__main__":
    asyncio.run(main())
