from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import ResumeRewriteReport, ResumeSchema, SkillGapReport


REWRITE_SYSTEM_PROMPT = """You are a Professional Resume Writer AI Agent.
Your job is to rewrite and optimize a candidate's resume bullet points and summary to align with a target Job Description using the STAR formula (Situation/Task, Action, Result) and Google's X-Y-Z formula ("Accomplished X as measured by Y by doing Z").

Guidelines:
1. Write a compelling, tailored professional summary targeted directly at the JD role.
2. For each work experience entry, rewrite bullet points to incorporate missing technical keywords from the skill gap report where relevant.
3. Quantify impact with estimated percentage improvements, cost savings, latency reductions, or team velocity metrics where applicable.
4. Keep original candidate achievements truthful while elevating tone, action verbs, and alignment.
"""


def get_resume_rewrite_agent():
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.2,
        timeout=180
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", REWRITE_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nJob Description:\n{job_description}\n\nSkill Gap Analysis:\n{skill_gap_json}")
    ])
    
    structured_llm = llm.with_structured_output(ResumeRewriteReport)
    return prompt | structured_llm


async def rewrite_resume(resume: ResumeSchema, job_description: str, skill_gap: SkillGapReport) -> ResumeRewriteReport:
    agent = get_resume_rewrite_agent()
    result = await agent.ainvoke({
        "resume_json": resume.model_dump_json(indent=2),
        "job_description": job_description,
        "skill_gap_json": skill_gap.model_dump_json(indent=2)
    })
    return result
