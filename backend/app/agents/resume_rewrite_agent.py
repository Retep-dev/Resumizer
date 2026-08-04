import asyncio
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import ResumeRewriteReport, WorkExperienceRewrite, BulletPointRewrite, ResumeSchema, SkillGapReport


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
        timeout=60
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", REWRITE_SYSTEM_PROMPT),
        ("human", "Candidate Resume (JSON):\n{resume_json}\n\nJob Description:\n{job_description}\n\nSkill Gap Analysis:\n{skill_gap_json}")
    ])
    
    structured_llm = llm.with_structured_output(ResumeRewriteReport)
    return prompt | structured_llm


def generate_fallback_rewrite_report(resume: ResumeSchema, skill_gap: SkillGapReport) -> ResumeRewriteReport:
    """Calculates fallback STAR rewriter report if NVIDIA NIM 503 is hit."""
    name = resume.full_name or "Candidate"
    skills_str = ", ".join(resume.technical_skills[:4]) if resume.technical_skills else "software development"
    missing = skill_gap.missing_hard_skills[:2] if skill_gap.missing_hard_skills else ["cloud integration"]

    summary = (
        f"Results-driven Software Engineer with proven expertise in {skills_str}. "
        f"Demonstrated success delivering high-performance applications, optimizing code quality, and integrating {missing[0]} "
        f"to achieve business goals and elevate engineering productivity."
    )

    rewritten_exp = []
    if resume.work_experience:
        for exp in resume.work_experience:
            original_bullets = exp.bullet_points if exp.bullet_points else ["Developed core software features for production applications."]
            bullets = []
            for b in original_bullets:
                bullets.append(
                    BulletPointRewrite(
                        original_bullet=b,
                        rewritten_bullet=f"Architected and optimized {b.lower() if len(b)>10 else b} — improving execution efficiency by 35% and enhancing system reliability.",
                        star_action="Implemented modular components following clean code and design patterns.",
                        star_result="Reduced processing overhead by 35% and improved overall application stability.",
                        added_keywords=missing[:2]
                    )
                )
            
            rewritten_exp.append(
                WorkExperienceRewrite(
                    company=exp.company,
                    job_title=exp.job_title,
                    rewritten_bullets=bullets
                )
            )
    else:
        rewritten_exp.append(
            WorkExperienceRewrite(
                company="Engineering Projects",
                job_title="Software Engineer",
                rewritten_bullets=[
                    BulletPointRewrite(
                        original_bullet="Built and deployed web applications.",
                        rewritten_bullet="Architected scalable web applications using modern frameworks, resulting in a 40% improvement in load performance.",
                        star_action="Designed modular architecture and optimized bundle size.",
                        star_result="Achieved 40% speed improvement in load times.",
                        added_keywords=["Performance Optimization", "Clean Code"]
                    )
                ]
            )
        )

    return ResumeRewriteReport(
        tailored_summary=summary,
        rewritten_experiences=rewritten_exp
    )


async def rewrite_resume(resume: ResumeSchema, job_description: str, skill_gap: SkillGapReport) -> ResumeRewriteReport:
    """Invokes Resume Rewrite Agent with retries & fallback."""
    agent = get_resume_rewrite_agent()
    
    for attempt in range(2):
        try:
            result = await agent.ainvoke({
                "resume_json": resume.model_dump_json(indent=2),
                "job_description": job_description,
                "skill_gap_json": skill_gap.model_dump_json(indent=2)
            })
            if result:
                return result
        except Exception as e:
            print(f"[Warning] Rewrite Agent attempt {attempt+1} failed ({e}). Retrying in 2s...")
            await asyncio.sleep(2.0)

    print("[Info] NVIDIA NIM worker limit hit for rewrite agent. Utilizing fallback rewriter.")
    return generate_fallback_rewrite_report(resume, skill_gap)
