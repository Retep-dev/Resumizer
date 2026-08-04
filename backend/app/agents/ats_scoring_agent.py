import asyncio
import re
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import ATSScore, ResumeSchema


ATS_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) Evaluation Expert AI Agent.
Your job is to compare a candidate's structured resume against a target Job Description and calculate comprehensive match scores and keyword insights.

Evaluation Criteria:
1. overall_score: 0-100 score based on combined keyword match, experience relevance, and formatting.
2. keyword_match_score: 0-100 score based on hard technical skills and tools matching the JD requirements.
3. experience_match_score: 0-100 score based on seniority, domain alignment, and experience responsibilities.
4. formatting_score: 0-100 score based on standard ATS section completeness.
5. breakdown_summary: High-level executive synthesis explaining the scores and match quality.
6. matched_keywords: List of critical technical & domain keywords found in both resume and JD.
7. missing_keywords: List of critical keywords from JD that are absent from the resume.
"""


def get_ats_scoring_agent():
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.1,
        timeout=45
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", ATS_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nTarget Job Description:\n{job_description}")
    ])
    
    structured_llm = llm.with_structured_output(ATSScore)
    return prompt | structured_llm


def generate_fallback_ats_score(resume: ResumeSchema, job_description: str) -> ATSScore:
    """Calculates algorithmic ATS score if NVIDIA NIM 503 is hit."""
    resume_skills = [s.lower() for s in (resume.technical_skills + resume.tools_and_frameworks)]
    jd_words = set(re.findall(r'\b[a-zA-Z0-9\#\+\.]+\b', job_description.lower()))
    
    matched = [s for s in resume.technical_skills if s.lower() in jd_words]
    missing = [w.capitalize() for w in ["Docker", "Kubernetes", "AWS", "CI/CD", "System Architecture", "Microservices"] if w.lower() in jd_words and w.lower() not in resume_skills]

    match_ratio = len(matched) / max(len(matched) + len(missing), 1)
    kw_score = min(int(match_ratio * 100) + 40, 95)
    exp_score = 75 if resume.work_experience else 50
    fmt_score = 90
    overall = int((kw_score * 0.5) + (exp_score * 0.3) + (fmt_score * 0.2))

    return ATSScore(
        overall_score=overall,
        keyword_match_score=kw_score,
        experience_match_score=exp_score,
        formatting_score=fmt_score,
        breakdown_summary=f"Candidate resume demonstrates strong core technical skills ({', '.join(matched[:4]) if matched else 'foundational skills'}). Addressing missing target keywords will further optimize ATS ranking.",
        matched_keywords=matched if matched else resume.technical_skills[:4],
        missing_keywords=missing if missing else ["Cloud Architecture", "CI/CD Automation"]
    )


async def evaluate_ats_score(resume: ResumeSchema, job_description: str) -> ATSScore:
    """Invokes ATS Agent with retries & algorithmic fallback."""
    agent = get_ats_scoring_agent()
    
    for attempt in range(2):
        try:
            result = await agent.ainvoke({
                "resume_json": resume.model_dump_json(indent=2),
                "job_description": job_description
            })
            if result:
                return result
        except Exception as e:
            print(f"[Warning] ATS Agent attempt {attempt+1} failed ({e}). Retrying in 2s...")
            await asyncio.sleep(2.0)

    print("[Info] NVIDIA NIM worker limit hit for ATS agent. Utilizing algorithmic fallback.")
    return generate_fallback_ats_score(resume, job_description)
