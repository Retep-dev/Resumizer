from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import InterviewPrepReport, ResumeSchema, SkillGapReport


INTERVIEW_GEN_SYSTEM_PROMPT = """You are an Interview Preparation AI Agent & Senior Technical Hiring Manager.
Your job is to generate exactly 6 highly tailored, realistic interview questions based on the candidate's background, the target job description, and identified skill gaps.

Mandatory Requirements:
1. Generate EXACTLY 6 questions in total:
   - 2 'behavioral' questions targeting teamwork, conflict resolution, and leadership.
   - 2 'technical' questions targeting core frameworks, architecture, and coding concepts in the JD.
   - 2 'gap_focused' questions addressing specific missing skills or experience gaps from the skill gap report.

2. For each question, provide:
   - question_type: Must be strictly one of 'behavioral', 'technical', or 'gap_focused'.
   - question: Clear, professional interview question.
   - context_or_reason: Why a hiring manager would ask this question.
   - star_guide: Step-by-step guidance for candidate to structure their answer using Situation, Task, Action, Result.
   - sample_answer: A complete, 100th-percentile sample response.
"""


def get_interview_generator_agent():
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.3,
        timeout=180
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", INTERVIEW_GEN_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nJob Description:\n{job_description}\n\nSkill Gap Report:\n{skill_gap_json}")
    ])
    
    structured_llm = llm.with_structured_output(InterviewPrepReport)
    return prompt | structured_llm


async def generate_interview_prep(resume: ResumeSchema, job_description: str, skill_gap: SkillGapReport) -> InterviewPrepReport:
    agent = get_interview_generator_agent()
    result = await agent.ainvoke({
        "resume_json": resume.model_dump_json(indent=2),
        "job_description": job_description,
        "skill_gap_json": skill_gap.model_dump_json(indent=2)
    })
    return result
