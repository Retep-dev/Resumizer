import asyncio
from app.schemas.resume import (
    ResumeSchema,
    AnalysisResult,
)
from app.agents.resume_parser_agent import parse_resume_text
from app.agents.ats_scoring_agent import evaluate_ats_score
from app.agents.skill_gap_agent import analyze_skill_gaps
from app.agents.resume_rewrite_agent import rewrite_resume
from app.agents.interview_generator_agent import generate_interview_prep


async def run_resumizer_pipeline(raw_resume_text: str, job_description: str) -> AnalysisResult:
    """
    Master Multi-Agent Orchestrator Pipeline for Resumizer.
    
    Flow (Sequential with light pauses to respect NVIDIA NIM rate/worker limits):
    1. Parse raw resume text into structured ResumeSchema.
    2. Evaluate ATS score.
    3. Analyze Skill Gaps.
    4. Rewrite experience bullet points.
    5. Generate Interview Preparation Questions.
    6. Assemble and return AnalysisResult.
    """
    # Step 1: Parse Resume
    parsed_resume = await parse_resume_text(raw_resume_text)
    await asyncio.sleep(0.5)

    # Step 2: Evaluate ATS Score
    ats_score = await evaluate_ats_score(parsed_resume, job_description)
    await asyncio.sleep(0.5)

    # Step 3: Analyze Skill Gaps
    skill_gap = await analyze_skill_gaps(parsed_resume, job_description)
    await asyncio.sleep(0.5)

    # Step 4: Rewrite Bullet Points
    rewrite_report = await rewrite_resume(parsed_resume, job_description, skill_gap)
    await asyncio.sleep(0.5)

    # Step 5: Generate Interview Questions
    interview_prep = await generate_interview_prep(parsed_resume, job_description, skill_gap)

    # Step 6: Assemble final result
    return AnalysisResult(
        resume_data=parsed_resume,
        ats_score=ats_score,
        skill_gap=skill_gap,
        rewrite_report=rewrite_report,
        interview_prep=interview_prep
    )
