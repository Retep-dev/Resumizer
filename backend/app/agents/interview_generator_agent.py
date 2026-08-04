from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import InterviewPrepReport, ResumeSchema, SkillGapReport


INTERVIEW_GEN_SYSTEM_PROMPT = """You are an Interview Preparation AI Agent & Technical Hiring Manager.
Your job is to generate a set of highly tailored interview questions based on the candidate's background, the target job description, and identified skill gaps.

Guidelines:
1. Generate behavioral questions targeting key leadership/teamwork aspects of the target job.
2. Generate hard technical questions relevant to the core technical stack in the JD.
3. Generate gap-focused questions addressing missing skills or experience gaps identified in the skill gap report.
4. For each question, provide:
   - question_type: 'behavioral', 'technical', or 'gap_focused'
   - question: The exact interview question
   - context_or_reason: Why an interviewer would ask this question
   - star_guide: How candidate should structure their answer using STAR
   - sample_answer: A top-scoring sample response model
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
