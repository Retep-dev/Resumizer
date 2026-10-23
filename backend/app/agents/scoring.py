"""Stage 2 — transparent, deterministic ATS scoring and skill-gap analysis.

The score is computed in code from defined criteria, not guessed by a model,
so the same resume and requirements always produce the same score.

    overall = 50% keywords + 30% experience + 20% formatting

* Keywords: share of the posting's requirements found in the resume text
  (required = weight 1, preferred = weight 0.5). Each match cites the line.
* Experience: 70% years of experience vs. the posting's minimum, 30% overlap
  between the posting's title and the candidate's job titles.
* Formatting: share of eight ATS-readability checks that pass.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from app.schemas.resume import (
    ATSScore, JobRequirements, KeywordEvidence, ResumeSchema, ScoreCriterion, SkillGapReport,
)
from app.services.text_utils import evidence_for, normalize, term_in_text, word_tokens_overlap, years_between

WEIGHTS = {"keywords": 0.5, "experience": 0.3, "formatting": 0.2}


def requirement_found(req, resume_text: str) -> Optional[str]:
    for t in [req.term] + list(req.aliases or []):
        if term_in_text(t, resume_text):
            return evidence_for(t, resume_text) or t
    return None


def candidate_years(resume: ResumeSchema, today: Optional[date] = None) -> Optional[float]:
    spans = [years_between(j.start_date, j.end_date, today) for j in resume.work_experience]
    spans = [s for s in spans if s is not None]
    return round(sum(spans), 1) if spans else None


def _keyword_criterion(reqs: JobRequirements, resume_text: str) -> Tuple[ScoreCriterion, List[KeywordEvidence]]:
    evidence: List[KeywordEvidence] = []
    total = got = 0.0
    for r in reqs.requirements:
        w = 1.0 if r.importance == "required" else 0.5
        ev = requirement_found(r, resume_text)
        evidence.append(KeywordEvidence(keyword=r.term, importance=r.importance, found=ev is not None, evidence=ev))
        total += w
        got += w if ev else 0
    if not total:
        return ScoreCriterion(name="Keywords", score=0, weight=WEIGHTS["keywords"],
                              detail="No skills or tools could be identified in the job description."), evidence
    found_req = sum(1 for e in evidence if e.found and e.importance == "required")
    n_req = sum(1 for e in evidence if e.importance == "required")
    score = round(100 * got / total)
    detail = f"{found_req} of {n_req} required and {sum(1 for e in evidence if e.found and e.importance == 'preferred')} of {len(evidence) - n_req} preferred keywords appear in your resume."
    return ScoreCriterion(name="Keywords", score=score, weight=WEIGHTS["keywords"], detail=detail), evidence


def _experience_criterion(resume: ResumeSchema, reqs: JobRequirements, today: Optional[date] = None) -> ScoreCriterion:
    years = candidate_years(resume, today)
    need = reqs.min_years
    parts = []
    if need and years is not None:
        years_part = min(1.0, years / need)
        parts.append(f"about {years:g} years of dated experience against {need}+ asked for")
    elif need:
        years_part = 0.5
        parts.append(f"the posting asks for {need}+ years but your roles have no readable dates")
    elif years is not None:
        years_part = 1.0 if years >= 2 else years / 2
        parts.append(f"about {years:g} years of dated experience (no minimum stated)")
    else:
        years_part = 0.5
        parts.append("no dated roles found")
    titles = " ".join(j.job_title for j in resume.work_experience)
    title_part = word_tokens_overlap(reqs.title, titles) if reqs.title else 0.5
    if reqs.title:
        parts.append(f"{round(title_part * 100)}% of the words in “{reqs.title}” appear in your job titles")
    score = round(100 * (0.7 * years_part + 0.3 * title_part))
    return ScoreCriterion(name="Experience", score=score, weight=WEIGHTS["experience"], detail=(lambda t: t[:1].upper() + t[1:])("; ".join(parts)) + ".")


def _formatting_criterion(resume: ResumeSchema, resume_text: str) -> ScoreCriterion:
    words = len(normalize(resume_text).split())
    jobs = resume.work_experience
    checks = [
        ("name", bool(resume.full_name)),
        ("email", bool(resume.email)),
        ("work experience", bool(jobs)),
        ("dates on every role", bool(jobs) and all(j.start_date for j in jobs)),
        ("bullet points under roles", bool(jobs) and sum(len(j.bullet_points) for j in jobs) >= 2 * len(jobs)),
        ("skills listed", bool(resume.technical_skills or resume.tools_and_frameworks)),
        ("education", bool(resume.education)),
        ("length 200–1,200 words", 200 <= words <= 1200),
    ]
    passed = [n for n, ok in checks if ok]
    failed = [n for n, ok in checks if not ok]
    score = round(100 * len(passed) / len(checks))
    detail = f"{len(passed)} of {len(checks)} readability checks pass" + (f"; missing: {', '.join(failed)}." if failed else ".")
    return ScoreCriterion(name="Formatting", score=score, weight=WEIGHTS["formatting"], detail=detail)


def score_resume(resume: ResumeSchema, resume_text: str, reqs: JobRequirements, method: str,
                 today: Optional[date] = None) -> Tuple[ATSScore, SkillGapReport]:
    kw, evidence = _keyword_criterion(reqs, resume_text)
    exp = _experience_criterion(resume, reqs, today)
    fmt = _formatting_criterion(resume, resume_text)
    overall = round(kw.score * kw.weight + exp.score * exp.weight + fmt.score * fmt.weight)

    matched = [e.keyword for e in evidence if e.found]
    missing = [e.keyword for e in evidence if not e.found]
    missing_required = [e.keyword for e in evidence if not e.found and e.importance == "required"]

    summary = (
        f"{kw.detail} {exp.detail} {fmt.detail} "
        f"Overall = 50% keywords ({kw.score}) + 30% experience ({exp.score}) + 20% formatting ({fmt.score})."
    )
    ats = ATSScore(
        overall_score=overall, keyword_match_score=kw.score, experience_match_score=exp.score, formatting_score=fmt.score,
        breakdown_summary=summary, matched_keywords=matched, missing_keywords=missing,
        criteria=[kw, exp, fmt], keyword_evidence=evidence, method=method,
    )

    by_cat = lambda cat, found: [e.keyword for e, r in zip(evidence, reqs.requirements) if r.category == cat and e.found == found]  # noqa: E731
    recs: List[str] = []
    for k in missing_required[:3]:
        recs.append(
            f"The posting asks for {k}, which your resume doesn't mention. If you have used it, add a bullet that says what you did with it. "
            f"If you haven't, leave it off and prepare to explain how you'd get up to speed."
        )
    if exp.score < 60 and reqs.min_years:
        recs.append(f"The role asks for {reqs.min_years}+ years. Make sure every role shows start and end dates so your full experience is counted.")
    if fmt.score < 100:
        recs.append(f"Fix the formatting gaps an ATS looks for: {fmt.detail.split('missing: ')[-1].rstrip('.')}.")
    gap = SkillGapReport(
        matched_hard_skills=by_cat("hard", True), missing_hard_skills=by_cat("hard", False),
        matched_soft_skills=by_cat("soft", True), missing_soft_skills=by_cat("soft", False),
        priority_skill_recommendations=recs, method=method,
    )
    return ats, gap
