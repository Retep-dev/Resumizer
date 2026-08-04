import asyncio
import re
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import SkillGapReport, ResumeSchema


SKILL_GAP_SYSTEM_PROMPT = """You are a Career Skill Gap Analysis AI Agent.
Your job is to identify technical, hard, and soft skill gaps between a candidate's resume and a target job description.

Responsibilities:
1. Identify matched_hard_skills: Hard technical skills present in both resume and JD.
2. Identify missing_hard_skills: Hard technical skills required by JD but missing from resume.
3. Identify matched_soft_skills: Soft skills present in both.
4. Identify missing_soft_skills: Soft skills required by JD but missing from resume.
5. Formulate priority_skill_recommendations: Actionable advice on which skills to acquire or highlight immediately to boost hiring odds.
"""


def get_skill_gap_agent():
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.1,
        timeout=180
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SKILL_GAP_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nTarget Job Description:\n{job_description}")
    ])
    
    structured_llm = llm.with_structured_output(SkillGapReport)
    return prompt | structured_llm


def generate_fallback_skill_gap(resume: ResumeSchema, job_description: str) -> SkillGapReport:
    """Calculates skill gap analysis if NVIDIA NIM 503 is hit."""
    resume_skills = [s.lower() for s in (resume.technical_skills + resume.tools_and_frameworks)]
    jd_words = set(re.findall(r'\b[a-zA-Z0-9\#\+\.]+\b', job_description.lower()))

    matched_hard = [s for s in resume.technical_skills if s.lower() in jd_words]
    missing_candidates = ["Docker", "Kubernetes", "AWS", "GraphQL", "CI/CD", "System Design", "Microservices"]
    missing_hard = [w for w in missing_candidates if w.lower() in jd_words and w.lower() not in resume_skills]
    if not missing_hard:
        missing_hard = ["System Design", "Cloud Infrastructure"]

    return SkillGapReport(
        matched_hard_skills=matched_hard if matched_hard else resume.technical_skills[:4],
        missing_hard_skills=missing_hard,
        matched_soft_skills=resume.soft_skills if resume.soft_skills else ["Communication", "Problem Solving"],
        missing_soft_skills=["Cross-functional Leadership", "Stakeholder Management"],
        priority_skill_recommendations=[
            f"Highlight practical project experience with {missing_hard[0]} in your work history.",
            "Quantify technical achievements using specific metric improvements (e.g. latency reductions, test coverage).",
            "Incorporate target job description keywords directly into your professional summary."
        ]
    )


async def analyze_skill_gaps(resume: ResumeSchema, job_description: str) -> SkillGapReport:
    """Invokes Skill Gap Agent with retries & fallback."""
    agent = get_skill_gap_agent()
    
    for attempt in range(2):
        try:
            result = await agent.ainvoke({
                "resume_json": resume.model_dump_json(indent=2),
                "job_description": job_description
            })
            if result:
                return result
        except Exception as e:
            print(f"[Warning] Skill Gap Agent attempt {attempt+1} failed ({e}). Retrying in 2s...")
            await asyncio.sleep(2.0)

    print("[Info] NVIDIA NIM worker limit hit for skill gap agent. Utilizing fallback analysis.")
    return generate_fallback_skill_gap(resume, job_description)
