import asyncio
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import InterviewPrepReport, InterviewQuestion, ResumeSchema, SkillGapReport


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
   - sample_answer: A complete, high-scoring sample response model.
"""


def get_interview_generator_agent():
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.3,
        timeout=45
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", INTERVIEW_GEN_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nJob Description:\n{job_description}\n\nSkill Gap Report:\n{skill_gap_json}")
    ])
    
    structured_llm = llm.with_structured_output(InterviewPrepReport)
    return prompt | structured_llm


def generate_fallback_interview_prep(resume: ResumeSchema, skill_gap: SkillGapReport) -> InterviewPrepReport:
    """Fallback generator in case NVIDIA NIM 503 worker limit is temporarily hit."""
    name = resume.full_name or "Candidate"
    missing = skill_gap.missing_hard_skills[:3] if skill_gap.missing_hard_skills else ["system design", "cloud architecture"]
    matched = resume.technical_skills[:3] if resume.technical_skills else ["frontend development", "problem solving"]

    questions = [
        InterviewQuestion(
            question_type="behavioral",
            question="Tell me about a complex project where you had to balance tight deadlines with code quality.",
            context_or_reason="Evaluates engineering discipline, prioritization, and communication under pressure.",
            star_guide="Describe the project scope (S), your specific responsibility (T), how you optimized delivery (A), and the quantifiable project outcome (R).",
            sample_answer="In my previous role, we had a critical 3-week deadline to launch a major feature. I broke the project into modular components, automated core unit tests, and communicated daily progress with stakeholders, launching on time with zero high-severity bugs."
        ),
        InterviewQuestion(
            question_type="behavioral",
            question="How do you handle technical disagreements or architectural decisions within an engineering team?",
            context_or_reason="Assesses collaboration, technical diplomacy, and objective decision-making.",
            star_guide="Outline a real technical dispute (S), your role (T), how you facilitated benchmarking or RFC discussions (A), and the agreed solution (R).",
            sample_answer="When deciding between REST and GraphQL for our new service, I created a lightweight benchmark prototype showcasing latency and bandwidth metrics for both. We presented the data objectively to the team and aligned on a hybrid approach."
        ),
        InterviewQuestion(
            question_type="technical",
            question=f"How do you design scalable applications using {matched[0] if matched else 'modern web frameworks'}?",
            context_or_reason=f"Tests core technical competency in {matched[0] if matched else 'your primary stack'}.",
            star_guide="Explain architecture principles (S/T), state management and caching strategies (A), and performance metrics achieved (R).",
            sample_answer=f"I structure applications into modular, reusable components with strict separation of concerns. I utilize state management tools, memoization, and lazy loading to keep bundle sizes minimal and render times fast."
        ),
        InterviewQuestion(
            question_type="technical",
            question="What strategies do you use for API error handling, asynchronous state, and performance optimization?",
            context_or_reason="Verifies production-readiness and fullstack robustness.",
            star_guide="Detail an API failure scenario (S/T), your implementation of retry mechanisms and global error boundaries (A), and user feedback outcomes (R).",
            sample_answer="I implement exponential backoff retries, centralized error interceptors, and user-friendly fallback UI states so that transient API issues never crash the user experience."
        ),
        InterviewQuestion(
            question_type="gap_focused",
            question=f"How would you quickly get up to speed with {missing[0] if missing else 'new backend tools'} required for this role?",
            context_or_reason=f"Addresses missing skill area ({missing[0] if missing else 'new technology'}) identified in job description.",
            star_guide="Reference a past instance where you learned a new technology rapidly (S/T), your self-directed learning approach (A), and the resulting production delivery (R).",
            sample_answer=f"I have a proven track record of rapid technology adoption. When I needed to learn a new framework in a previous role, I built a hands-on proof-of-concept project within a week, mastered the core concepts, and successfully delivered production features shortly after."
        ),
        InterviewQuestion(
            question_type="gap_focused",
            question=f"Can you discuss how your experience in {matched[0] if matched else 'your domain'} translates to working with {missing[1] if len(missing)>1 else 'distributed systems'}?",
            context_or_reason="Evaluates transferability of skills to bridge target role qualifications.",
            star_guide="Connect foundational engineering principles (S/T), cross-skilling efforts (A), and value brought to the team (R).",
            sample_answer="Core software engineering principles like clean code, modular architecture, and thorough testing apply universally across stacks. My deep understanding of state flow and API design allows me to quickly master new paradigms and contribute effectively."
        )
    ]
    return InterviewPrepReport(questions=questions)


async def generate_interview_prep(resume: ResumeSchema, job_description: str, skill_gap: SkillGapReport) -> InterviewPrepReport:
    """Attempts agent invocation with retries; falls back gracefully if 503 ResourceExhausted occurs."""
    agent = get_interview_generator_agent()
    
    for attempt in range(2):
        try:
            result = await agent.ainvoke({
                "resume_json": resume.model_dump_json(indent=2),
                "job_description": job_description,
                "skill_gap_json": skill_gap.model_dump_json(indent=2)
            })
            if result and result.questions and len(result.questions) > 0:
                return result
        except Exception as e:
            print(f"[Warning] Interview Agent attempt {attempt+1} failed ({e}). Retrying...")
            await asyncio.sleep(1.5)

    print("[Info] NVIDIA NIM worker limit hit for interview agent. Utilizing tailored fallback prep.")
    return generate_fallback_interview_prep(resume, skill_gap)
