"""Stage 3a — rewrite bullets for clarity and relevance without inventing facts."""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.llm import ChatClient, complete_json
from app.schemas.resume import BulletPointRewrite, ResumeRewriteReport, ResumeSchema, WorkExperienceRewrite
from app.services.text_utils import normalize, term_in_text, unsupported_numbers

REWRITE_SYSTEM_PROMPT = """You are a careful resume editor. You improve how existing achievements are worded. You never add facts.

Hard rules:
1. Keep the meaning of every bullet. Do not add tools, skills, employers, responsibilities, team sizes or outcomes that the original bullet doesn't state.
2. Never add a number, percentage, amount or duration that isn't in the original bullet. If a metric would make a bullet stronger, keep the bullet without it and ask for it in "needs_confirmation" (e.g. "How many tests did you run, and what changed as a result?").
3. You may: start with a strong action verb, tighten wording, put the result first, and use the posting's terminology where the original bullet already describes that thing.
4. "added_keywords" lists only posting keywords that the original bullet genuinely supports. Never use a keyword from the "missing" list.
5. "star_action" and "star_result" restate what the bullet says; leave star_result empty if the bullet has no result.
6. The summary may only use facts present in the resume. Don't state years of experience unless the resume does.

Return one JSON object:
{"tailored_summary": str|null,
 "rewritten_experiences": [{"company": str, "job_title": str,
   "rewritten_bullets": [{"original_bullet": str, "rewritten_bullet": str, "star_action": str, "star_result": str,
                          "added_keywords": [str], "needs_confirmation": [str]}]}]}
Include every bullet from the resume, with original_bullet copied exactly."""


class _Draft(BaseModel):
    tailored_summary: Optional[str] = None
    rewritten_experiences: List[WorkExperienceRewrite] = Field(default_factory=list)


def _norm(s: str) -> str:
    return " ".join(normalize(s).lower().split()).strip(" .")


def check_bullet(rw: BulletPointRewrite, original: str, missing: List[str], supported: List[str]) -> List[str]:
    """Reasons a rewrite isn't trustworthy (empty list = fine)."""
    problems = []
    bad_nums = unsupported_numbers(rw.rewritten_bullet, original)
    if bad_nums:
        problems.append(f"added numbers that aren't in the original ({', '.join(sorted(bad_nums))})")
    claimed = [k for k in missing if term_in_text(k, rw.rewritten_bullet) and not term_in_text(k, original)]
    if claimed:
        problems.append(f"claimed {', '.join(claimed)}, which your resume doesn't show")
    return problems


def _clean(rw: BulletPointRewrite, original: str, supported: List[str]) -> BulletPointRewrite:
    keywords = [k for k in rw.added_keywords if any(_norm(k) == _norm(s) for s in supported) and term_in_text(k, rw.rewritten_bullet)]
    result = rw.star_result if not unsupported_numbers(rw.star_result, original) else ""
    action = rw.star_action if not unsupported_numbers(rw.star_action, original) else ""
    return BulletPointRewrite(
        original_bullet=original, rewritten_bullet=rw.rewritten_bullet.strip(), star_action=action, star_result=result,
        added_keywords=keywords, needs_confirmation=[q for q in rw.needs_confirmation if q.strip()][:3], status="rewritten",
    )


def validate_rewrites(draft: _Draft, resume: ResumeSchema, resume_text: str, missing: List[str], supported: List[str]
                      ) -> Tuple[ResumeRewriteReport, Dict[str, List[str]], List[str]]:
    """Match each rewrite to a real bullet and withhold any that add facts."""
    originals = {_norm(b): (ji, b) for ji, j in enumerate(resume.work_experience) for b in j.bullet_points}
    out: Dict[int, List[BulletPointRewrite]] = {}
    violations: Dict[str, List[str]] = {}
    for exp in draft.rewritten_experiences:
        for rw in exp.rewritten_bullets:
            hit = originals.get(_norm(rw.original_bullet))
            if not hit:
                continue  # model referenced a bullet that doesn't exist
            ji, original = hit
            problems = check_bullet(rw, original, missing, supported)
            if problems:
                violations[original] = problems
                out.setdefault(ji, []).append(BulletPointRewrite(
                    original_bullet=original, rewritten_bullet=original, status="kept_original",
                    note="Rewrite withheld: it " + " and ".join(problems) + ".",
                    needs_confirmation=[q for q in rw.needs_confirmation if q.strip()][:3],
                ))
            else:
                out.setdefault(ji, []).append(_clean(rw, original, supported))

    warnings = []
    summary = draft.tailored_summary.strip() if draft.tailored_summary else None
    if summary:
        bad = unsupported_numbers(summary, resume_text)
        claimed = [k for k in missing if term_in_text(k, summary) and not term_in_text(k, resume_text)]
        if bad or claimed:
            warnings.append("The suggested summary was withheld because it stated facts that aren't in your resume.")
            summary = None

    exps = []
    for ji, job in enumerate(resume.work_experience):
        seen, bullets = set(), []
        for b in out.get(ji, []):
            if b.original_bullet not in seen:
                seen.add(b.original_bullet)
                bullets.append(b)
        if bullets:
            exps.append(WorkExperienceRewrite(company=job.company, job_title=job.job_title, rewritten_bullets=bullets))
    return ResumeRewriteReport(tailored_summary=summary, rewritten_experiences=exps), violations, warnings


async def rewrite_with_ai(client: ChatClient, resume: ResumeSchema, resume_text: str, job_description: str,
                          supported: List[str], missing: List[str]) -> Tuple[ResumeRewriteReport, List[str], str]:
    if not any(j.bullet_points for j in resume.work_experience):
        return ResumeRewriteReport(), ["No bullet points were found under your roles, so there was nothing to rewrite."], ""
    payload = {
        "resume": json.loads(resume.model_dump_json(include={"summary", "work_experience", "technical_skills", "tools_and_frameworks"})),
        "posting_keywords_supported_by_resume": supported,
        "missing_keywords_do_not_use": missing,
    }
    user = f"Resume and keyword lists (JSON):\n{json.dumps(payload, ensure_ascii=False)}\n\nJob description:\n{job_description[:6000]}"
    draft, model = await complete_json(client, REWRITE_SYSTEM_PROMPT, user, _Draft, temperature=0.2, max_tokens=4000)
    report, violations, warnings = validate_rewrites(draft, resume, resume_text, missing, supported)

    if violations:
        # One targeted retry for the bullets that broke the rules.
        fix_user = user + "\n\nYour previous rewrites of these bullets broke the rules:\n" + "\n".join(
            f"- {b!r}: {', '.join(p)}" for b, p in violations.items()
        ) + "\nRewrite only these bullets again, following the rules strictly. Same JSON format."
        try:
            fix, _ = await complete_json(client, REWRITE_SYSTEM_PROMPT, fix_user, _Draft, temperature=0.0, max_tokens=2500)
            fixed, still_bad, _ = validate_rewrites(fix, resume, resume_text, missing, supported)
            good = {b.original_bullet: b for e in fixed.rewritten_experiences for b in e.rewritten_bullets if b.status == "rewritten"}
            for e in report.rewritten_experiences:
                e.rewritten_bullets = [good.get(b.original_bullet, b) if b.status == "kept_original" else b for b in e.rewritten_bullets]
        except Exception:
            pass  # keep the withheld originals
    withheld = sum(1 for e in report.rewritten_experiences for b in e.rewritten_bullets if b.status == "kept_original")
    if withheld:
        warnings.append(f"{withheld} rewrite(s) were withheld because they added facts that aren't in your resume; the original wording is shown instead.")
    return report, warnings, model
