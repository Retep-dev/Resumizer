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
        temperature=0.1
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SKILL_GAP_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nTarget Job Description:\n{job_description}")
    ])
    
    structured_llm = llm.with_structured_output(SkillGapReport)
    return prompt | structured_llm


async def analyze_skill_gaps(resume: ResumeSchema, job_description: str) -> SkillGapReport:
    agent = get_skill_gap_agent()
    result = await agent.ainvoke({
        "resume_json": resume.model_dump_json(indent=2),
        "job_description": job_description
    })
    return result
