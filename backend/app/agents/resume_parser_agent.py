"""Stage 1a — turn raw resume text into ResumeSchema, grounded in that text."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.agents.safety import UNTRUSTED_DATA_NOTE
from app.llm import ChatClient, complete_json
from app.schemas.resume import Education, Project, ResumeSchema, WorkExperience
from app.services.text_utils import normalize, term_in_text, word_tokens_overlap

MAX_RESUME_CHARS = 12000

PARSER_SYSTEM_PROMPT = """You extract facts from a resume into JSON. The resume text is the only source of truth.

Rules:
- Copy names, employers, job titles, dates, degrees and institutions exactly as written. Do not correct, expand or guess them.
- Copy each bullet point verbatim (you may drop the leading bullet symbol). Do not merge, shorten or rewrite bullets.
- A job title and an employer are different things. Never use a section heading (e.g. "Experience") as an employer.
- Put a skill in technical_skills, tools_and_frameworks or soft_skills only if it is written in the resume.
- If something is not in the resume, use null or an empty list. Never invent placeholders.
- Contact lines, section headings and dates are not bullet points.

Return one JSON object with exactly these keys:
{"full_name": str, "email": str|null, "phone": str|null, "location": str|null, "linkedin": str|null, "github": str|null,
 "summary": str|null, "technical_skills": [str], "soft_skills": [str], "tools_and_frameworks": [str],
 "work_experience": [{"company": str, "job_title": str, "location": str|null, "start_date": str|null, "end_date": str|null, "bullet_points": [str]}],
 "education": [{"institution": str, "degree": str, "field_of_study": str|null, "graduation_year": str|null}],
 "certifications": [str], "projects": [{"name": str, "description": str, "technologies": [str], "link": str|null}]}"""
PARSER_SYSTEM_PROMPT += UNTRUSTED_DATA_NOTE


# ───────────────────────── Grounding ─────────────────────────

# Placeholders a model (or the old fallback) might emit instead of a real name.
_GENERIC = {
    "university", "college", "school", "institute", "company", "employer", "organization", "organisation",
    "experience", "work experience", "engineering experience", "professional experience", "n/a", "na",
    "unknown", "none", "candidate", "various", "freelance projects",
}


def _supported(value: Optional[str], text: str, threshold: float = 0.85) -> bool:
    if not value or not value.strip() or value.strip().lower() in _GENERIC:
        return False
    if term_in_text(value, text):
        return True
    return any(word_tokens_overlap(value, line) >= threshold for line in normalize(text).splitlines() if line.strip())


def _literal(value: Optional[str], text: str) -> Optional[str]:
    """Keep contact details only if they appear verbatim (case-insensitive)."""
    if value and normalize(value).lower().strip() in normalize(text).lower():
        return value.strip()
    return None


def ground_resume(resume: ResumeSchema, raw_text: str) -> Tuple[ResumeSchema, List[str]]:
    """Remove anything the model returned that the resume text doesn't support."""
    warnings: List[str] = []
    text = normalize(raw_text)

    name = resume.full_name.strip()
    if name and not _supported(name, text, 1.0):
        warnings.append("The extracted name wasn't found in your resume, so it was left blank.")
        name = ""

    jobs: List[WorkExperience] = []
    dropped_bullets = 0
    for job in resume.work_experience:
        has_title = _supported(job.job_title, text)
        has_company = _supported(job.company, text)
        if not has_title and not has_company:
            warnings.append(f"Removed a role (“{job.job_title or job.company}”) that isn't in your resume.")
            continue
        bullets = [b for b in job.bullet_points if _supported(b, text, 0.8)]
        dropped_bullets += len(job.bullet_points) - len(bullets)
        dates_ok = lambda d: bool(d) and all(y in text for y in re.findall(r"\d{4}", d))  # noqa: E731
        jobs.append(WorkExperience(
            company=job.company.strip() if has_company else "",
            job_title=job.job_title.strip() if has_title else "",
            location=job.location if _supported(job.location, text) else None,
            start_date=job.start_date if dates_ok(job.start_date) or (job.start_date and _supported(job.start_date, text)) else None,
            end_date=job.end_date if dates_ok(job.end_date) or (job.end_date and _supported(job.end_date, text)) else None,
            bullet_points=bullets,
        ))
    if dropped_bullets:
        warnings.append(f"Removed {dropped_bullets} bullet point(s) that didn't match your resume text.")

    def skills(items: List[str]) -> List[str]:
        seen, out = set(), []
        for s in items:
            k = s.strip().lower()
            if s.strip() and k not in seen and term_in_text(s, text):
                seen.add(k)
                out.append(s.strip())
        return out

    education = [
        Education(
            institution=e.institution.strip(),
            degree=e.degree.strip() if _supported(e.degree, text) else "",
            field_of_study=e.field_of_study if _supported(e.field_of_study, text) else None,
            graduation_year=e.graduation_year if e.graduation_year and e.graduation_year in text else None,
        )
        for e in resume.education
        if _supported(e.institution, text)
    ]
    projects = [
        Project(name=p.name.strip(), description=p.description if _supported(p.description, text, 0.6) else "",
                technologies=skills(p.technologies), link=_literal(p.link, text))
        for p in resume.projects if _supported(p.name, text)
    ]

    grounded = ResumeSchema(
        full_name=name,
        email=_literal(resume.email, text),
        phone=_literal(resume.phone, text),
        location=resume.location if _supported(resume.location, text) else None,
        linkedin=_literal(resume.linkedin, text),
        github=_literal(resume.github, text),
        summary=resume.summary if _supported(resume.summary, text, 0.7) else None,
        technical_skills=skills(resume.technical_skills),
        soft_skills=skills(resume.soft_skills),
        tools_and_frameworks=skills(resume.tools_and_frameworks),
        work_experience=jobs,
        education=education,
        certifications=[c for c in resume.certifications if _supported(c, text)],
        projects=projects,
    )
    return grounded, warnings


async def parse_resume_with_ai(client: ChatClient, raw_text: str) -> Tuple[ResumeSchema, List[str], str]:
    parsed, model = await complete_json(
        client, PARSER_SYSTEM_PROMPT, f"Resume text:\n\n{raw_text[:MAX_RESUME_CHARS]}", ResumeSchema,
        temperature=0.0, max_tokens=4000,
    )
    grounded, warnings = ground_resume(parsed, raw_text)
    return grounded, warnings, model


# ───────────────────────── Rule-based parser (AI unavailable) ─────────────────────────

_SECTION_RE = re.compile(
    r"^\s*(professional\s+summary|summary|profile|objective|about|work\s+experience|professional\s+experience|"
    r"experience|employment(?:\s+history)?|career\s+history|education|academic\s+background|skills|technical\s+skills|"
    r"core\s+skills|key\s+skills|tools|projects|certifications|licenses|awards)\s*:?\s*$",
    re.IGNORECASE,
)
_DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\.?\s+)?(?:\d{1,2}[/.])?(?:19|20)\d{2})\s*(?:-|to|–|—)\s*"
    r"(?P<end>(?:[A-Za-z]{3,9}\.?\s+)?(?:\d{1,2}[/.])?(?:19|20)\d{2}|present|current|now)",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^\s*[•●▪◦‣∙·*\-–—]\s+")
_DEGREE_RE = re.compile(r"\b(B\.?Sc|B\.?A|B\.?Eng|BS|BA|M\.?Sc|M\.?A|MBA|MS|M\.?Eng|Ph\.?D|Bachelor|Master|Doctor|Diploma|Associate|HND|OND)\b", re.IGNORECASE)
_SCHOOL_RE = re.compile(r"\b(University|College|Institute|School|Academy|Polytechnic)\b", re.IGNORECASE)


def _section_of(heading: str) -> str:
    h = heading.lower()
    if any(k in h for k in ("experience", "employment", "career")):
        return "experience"
    if "education" in h or "academic" in h:
        return "education"
    if "skill" in h or h.strip() == "tools":
        return "skills"
    if "project" in h:
        return "projects"
    if "certif" in h or "licen" in h:
        return "certifications"
    if any(k in h for k in ("summary", "profile", "objective", "about")):
        return "summary"
    return "other"


def _split_header(header: str) -> Tuple[str, str, Optional[str]]:
    """'Title, Company - City' / 'Title - Company' / 'Title at Company' → (title, company, location)."""
    parts = [p.strip(" ,|-") for p in re.split(r"\s+-\s+|\s+\|\s+|\s+at\s+|,\s+|\s+@\s+", header) if p.strip(" ,|-")]
    if not parts:
        return "", "", None
    return parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else None


def rule_based_parse(raw_text: str) -> Tuple[ResumeSchema, List[str]]:
    """Pattern-based extraction that only ever copies text from the resume."""
    text = normalize(raw_text)
    lines = [l.rstrip() for l in text.splitlines()]
    warnings = ["The AI parser was unavailable, so your resume was read with simple patterns. Check that roles, employers and dates look right."]

    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = re.search(r"\+?\d[\d\s().-]{7,}\d", text)
    linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s|,]+", text, re.IGNORECASE)
    github = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s|,]+", text, re.IGNORECASE)

    name = ""
    for l in lines[:5]:
        s = l.strip()
        if s and re.fullmatch(r"[A-Za-zÀ-ÿ'’.\- ]{3,60}", s) and 2 <= len(s.split()) <= 4 and not _SECTION_RE.match(s):
            name = s
            break

    sections = {}
    current = "header"
    for l in lines:
        if _SECTION_RE.match(l.strip()) and len(l.strip()) <= 40:
            current = _section_of(l)
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(l)

    jobs: List[WorkExperience] = []
    for l in sections.get("experience", []):
        s = l.strip()
        if not s:
            continue
        m = _DATE_RANGE_RE.search(s)
        if m and not _BULLET_RE.match(s):
            header = (s[: m.start()] + s[m.end():]).strip(" ()|,-\t")
            header = re.sub(r"\(\s*\)", "", header).strip(" ()|,-")
            title, company, location = _split_header(header)
            jobs.append(WorkExperience(job_title=title, company=company, location=location,
                                       start_date=m.group("start"), end_date=m.group("end")))
        elif jobs and (_BULLET_RE.match(s) or len(s) > 25):
            jobs[-1].bullet_points.append(_BULLET_RE.sub("", s).strip())

    skills: List[str] = []
    for l in sections.get("skills", []):
        body = l.split(":", 1)[1] if ":" in l and len(l.split(":", 1)[0]) < 30 else l
        for part in re.split(r"[,;|•·]", _BULLET_RE.sub("", body)):
            p = part.strip(" .")
            if 1 < len(p) <= 40 and p.lower() not in {x.lower() for x in skills}:
                skills.append(p)

    education: List[Education] = []
    for l in sections.get("education", []):
        s = _BULLET_RE.sub("", l.strip())
        if not s:
            continue
        parts = [p.strip() for p in re.split(r",| - | \| ", s) if p.strip()]
        inst = next((p for p in parts if _SCHOOL_RE.search(p)), "")
        deg = next((p for p in parts if _DEGREE_RE.search(p)), "")
        year = re.search(r"(19|20)\d{2}", s)
        if inst or deg:
            education.append(Education(institution=inst, degree=deg, graduation_year=year.group(0) if year else None))

    summary = " ".join(l.strip() for l in sections.get("summary", []) if l.strip()) or None
    certs = [_BULLET_RE.sub("", l).strip() for l in sections.get("certifications", []) if l.strip()]

    if not jobs:
        warnings.append("No roles with dates were found, so work experience is empty.")
    elif any(not j.company for j in jobs):
        warnings.append("Some employers couldn't be separated from job titles.")

    return ResumeSchema(
        full_name=name,
        email=email.group(0) if email else None,
        phone=phone.group(0).strip() if phone else None,
        linkedin=linkedin.group(0) if linkedin else None,
        github=github.group(0) if github else None,
        summary=summary,
        technical_skills=skills,
        work_experience=jobs,
        education=education,
        certifications=certs,
    ), warnings
