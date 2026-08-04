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
        timeout=180
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", ATS_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nTarget Job Description:\n{job_description}")
    ])
    
    structured_llm = llm.with_structured_output(ATSScore)
    return prompt | structured_llm


async def evaluate_ats_score(resume: ResumeSchema, job_description: str) -> ATSScore:
    agent = get_ats_scoring_agent()
    result = await agent.ainvoke({
        "resume_json": resume.model_dump_json(indent=2),
        "job_description": job_description
    })
    return result
