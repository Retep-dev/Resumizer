"""Stage 1b — extract requirements from the job description, independently of the resume."""
from __future__ import annotations

import re
from typing import List, Tuple

from app.llm import ChatClient, complete_json
from app.schemas.resume import JobRequirement, JobRequirements
from app.services.text_utils import normalize, required_years, term_in_text

MAX_JD_CHARS = 10000

JOB_SYSTEM_PROMPT = """You read a job description and list what it asks candidates for. You do not see any resume.

Rules:
- List each distinct skill, tool, technology, method, qualification or soft skill that the posting names.
- "term" is the skill itself in 1-4 words, using the posting's wording but without qualifiers: "Expert Python and SQL" → two terms "Python" and "SQL"; "Strong stakeholder communication" → "Stakeholder communication".
- Years of experience are NOT terms; put the minimum in min_years only.
- Add common alternative spellings to "aliases" (e.g. "A/B testing" → ["AB testing", "split testing"]).
- category: "hard" for technical skills, tools, methods and qualifications; "soft" for interpersonal or working-style skills.
- importance: "preferred" if the posting marks it as a plus, nice-to-have, bonus or preferred; otherwise "required".
- Do not add requirements the posting doesn't state. Do not list generic words like "experience" or "team".
- min_years: the minimum years of experience the posting asks for, or null.
- title: the job title, or null.

Return one JSON object: {"title": str|null, "min_years": int|null,
 "requirements": [{"term": str, "category": "hard"|"soft", "importance": "required"|"preferred", "aliases": [str]}]}"""


_QUALIFIER_RE = re.compile(r"^(?:strong|expert|excellent|proven|solid|advanced|deep|good|great|demonstrated|hands-on|working)\s+(?:knowledge\s+of\s+|experience\s+(?:with|in)\s+)?", re.IGNORECASE)
_DURATION_RE = re.compile(r"\b\d+\s*\+?\s*(?:years?|yrs?)\b|\byears? of experience\b", re.IGNORECASE)


def clean_term(term: str) -> str:
    """'Strong stakeholder communication' → 'stakeholder communication'; drop durations."""
    original = term.strip()
    t = _QUALIFIER_RE.sub("", original).strip(" .,:;")
    if _DURATION_RE.search(t) or len(t.split()) > 5:
        return ""
    # Only re-capitalise when a qualifier was removed, so "dbt" stays "dbt".
    return t[:1].upper() + t[1:] if t != original else t


def ground_requirements(reqs: JobRequirements, jd: str) -> Tuple[JobRequirements, List[str]]:
    """Keep only requirements whose term (or an alias) is actually in the posting."""
    kept, dropped, seen = [], 0, set()
    for r in reqs.requirements:
        term = clean_term(r.term)
        if not term or term.lower() in seen:
            continue
        if term_in_text(term, jd) or any(term_in_text(a, jd) for a in r.aliases):
            seen.add(term.lower())
            kept.append(JobRequirement(term=term, category=r.category, importance=r.importance, aliases=[a for a in r.aliases if a.strip()][:5]))
        else:
            dropped += 1
    warnings = [f"Ignored {dropped} requirement(s) the AI listed that aren't in the job description."] if dropped else []
    kept, added = backfill_known_skills(kept, jd)
    kept = merge_alternatives(kept, jd)
    if added:
        warnings.append(f"Added {len(added)} skill(s) the AI missed but the posting names: {', '.join(added)}.")
    years = reqs.min_years if reqs.min_years and str(reqs.min_years) in jd else required_years(jd)
    title = reqs.title if reqs.title and term_in_text(reqs.title, jd) else _title_guess(jd)
    return JobRequirements(title=title, min_years=years, requirements=kept[:40]), warnings


def merge_alternatives(reqs: List[JobRequirement], jd: str) -> List[JobRequirement]:
    """'Snowflake or BigQuery' is one requirement: having either satisfies it.

    Requirements whose terms appear in the posting joined by "or" or "/" are
    merged; the merged term's aliases are the alternatives, so scoring finds a
    match when the resume shows any of them.
    """
    text = normalize(jd).lower()
    parent = list(range(len(reqs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # Replace each term in the posting with a marker, longest first, so "React"
    # inside "React Testing Library" isn't read as a separate alternative.
    marked = text
    for i in sorted(range(len(reqs)), key=lambda k: -len(reqs[k].term)):
        marked = re.sub(rf"(?<![a-z0-9\u27e6]){re.escape(reqs[i].term.lower())}(?![a-z0-9])", f"\u27e6{i}\u27e7", marked)
    for m in re.finditer(r"\u27e6(\d+)\u27e7(?=\s*(?:,\s*)?(?:or|/)\s*\u27e6(\d+)\u27e7)", marked):
        i, j = int(m.group(1)), int(m.group(2))
        if i != j and reqs[i].category == reqs[j].category:
            parent[find(j)] = find(i)
    groups = {}
    for i in range(len(reqs)):
        groups.setdefault(find(i), []).append(reqs[i])
    out = []
    for i in range(len(reqs)):
        if find(i) == i and len(groups[i]) == 1 and re.search(r"\s+or\s+", groups[i][0].term):
            # The AI already combined them: make each alternative an alias.
            r = groups[i][0]
            parts = [p.strip() for p in re.split(r"\s+or\s+|,", r.term) if p.strip()]
            out.append(JobRequirement(term=r.term, category=r.category, importance=r.importance,
                                      aliases=list(dict.fromkeys(parts + list(r.aliases)))[:8]))
            continue
        if find(i) != i:
            continue
        g = groups[i]
        if len(g) == 1:
            out.append(g[0])
            continue
        aliases = list(dict.fromkeys([r.term for r in g] + [a for r in g for a in r.aliases]))
        out.append(JobRequirement(
            term=" or ".join(r.term for r in g), category=g[0].category,
            importance="required" if any(r.importance == "required" for r in g) else "preferred",
            aliases=aliases[:8],
        ))
    return out


def backfill_known_skills(reqs: List[JobRequirement], jd: str) -> Tuple[List[JobRequirement], List[str]]:
    """Add well-known technical skills the posting names but the AI left out."""
    text = normalize(jd)
    lines = text.splitlines()
    covered = [t for r in reqs for t in [r.term] + list(r.aliases)]
    added = []
    for term in HARD_SKILLS:
        if term in ("R", "Go") or not term_in_text(term, text):
            continue
        if any(term_in_text(term, c) or term_in_text(c, term) for c in covered):
            continue
        line = next((l for l in lines if term_in_text(term, l)), "")
        reqs.append(JobRequirement(term=term, category="hard", importance="preferred" if _PREFERRED_RE.search(line) else "required"))
        covered.append(term)
        added.append(term)
    return reqs, added


async def analyze_job_with_ai(client: ChatClient, jd: str) -> Tuple[JobRequirements, List[str], str]:
    reqs, model = await complete_json(client, JOB_SYSTEM_PROMPT, f"Job description:\n\n{jd[:MAX_JD_CHARS]}", JobRequirements, temperature=0.0, max_tokens=2500)
    grounded, warnings = ground_requirements(reqs, jd)
    return grounded, warnings, model


# ───────────────────────── Rule-based extraction ─────────────────────────

HARD_SKILLS = [
    # languages & data
    "Python", "SQL", "R", "Java", "JavaScript", "TypeScript", "Go", "Golang", "C#", "C++", "Rust", "Scala", "Kotlin", "Swift", "PHP", "Ruby",
    "HTML", "CSS", "Bash", "Excel", "VBA", "Power BI", "Tableau", "Looker", "Amplitude", "Mixpanel", "Google Analytics", "Snowflake",
    "BigQuery", "Redshift", "Databricks", "Spark", "Hadoop", "Kafka", "Airflow", "dbt", "Pandas", "NumPy", "scikit-learn", "TensorFlow",
    "PyTorch", "Machine learning", "Deep learning", "NLP", "Statistics", "A/B testing", "Experimentation", "Causal inference",
    "Regression", "Forecasting", "Cohort analysis", "Retention", "Data modeling", "ETL", "Data visualization", "Data warehousing",
    # engineering
    "React", "Next.js", "Vue", "Angular", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring", ".NET", "GraphQL", "REST",
    "REST API", "Microservices", "System design", "Docker", "Kubernetes", "Terraform", "AWS", "Azure", "GCP", "Google Cloud", "CI/CD",
    "Git", "Linux", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Unit testing", "Security", "DevOps",
    # product, design, business
    "Product management", "Roadmapping", "Agile", "Scrum", "Jira", "Figma", "Sketch", "Adobe Creative Suite", "Photoshop", "Illustrator",
    "UX research", "User research", "Prototyping", "Wireframing", "Accessibility", "SEO", "SEM", "Content marketing", "Salesforce",
    "HubSpot", "CRM", "Financial modeling", "Budgeting", "Accounting", "IFRS", "GAAP", "Project management", "PMP", "Six Sigma",
    "Supply chain management", "Customer success", "Copywriting",
]
SOFT_SKILLS = [
    "Communication", "Stakeholder management", "Stakeholder communication", "Leadership", "Mentoring", "Collaboration", "Teamwork",
    "Problem solving", "Critical thinking", "Presentation", "Storytelling", "Executive storytelling", "Negotiation", "Time management",
    "Attention to detail", "Adaptability", "Ownership", "Cross-functional", "Coaching", "Prioritization", "Decision making",
]
_PREFERRED_RE = re.compile(r"\b(nice to have|nice-to-have|a plus|bonus|preferred|desirable|ideally)\b", re.IGNORECASE)


def _title_guess(jd: str):
    for line in normalize(jd).splitlines():
        s = line.strip()
        if s:
            s = re.split(r"\s+-\s+|\(|\|", s)[0].strip()
            return s if 3 <= len(s) <= 80 else None
    return None


def rule_based_requirements(jd: str) -> Tuple[JobRequirements, List[str]]:
    text = normalize(jd)
    lines = text.splitlines()
    reqs: List[JobRequirement] = []
    seen = set()
    for category, vocab in (("hard", HARD_SKILLS), ("soft", SOFT_SKILLS)):
        for term in vocab:
            if term.lower() in seen or not term_in_text(term, text):
                continue
            # 'R' and 'Go' are too ambiguous without context.
            if term in ("R", "Go") and not re.search(rf"\b{term}\b(?:\s*(?:,|and|or|/))", text):
                continue
            line = next((l for l in lines if term_in_text(term, l)), "")
            importance = "preferred" if _PREFERRED_RE.search(line) else "required"
            seen.add(term.lower())
            reqs.append(JobRequirement(term=term, category=category, importance=importance))
    reqs = merge_alternatives(reqs, text)
    warnings = ["The AI was unavailable, so requirements were matched against a fixed skills list; unusual skills in the posting may be missed."]
    return JobRequirements(title=_title_guess(jd), min_years=required_years(jd), requirements=reqs), warnings
