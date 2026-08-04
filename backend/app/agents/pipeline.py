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
    Optimized Parallel Multi-Agent Orchestrator Pipeline for Resumizer.
    
    Flow:
    Stage 1: Parse raw resume text into structured ResumeSchema.
    Stage 2: Evaluate ATS score & Analyze Skill Gaps concurrently in PARALLEL.
    Stage 3: Rewrite Experience bullets & Generate Interview Prep concurrently in PARALLEL.
    Stage 4: Assemble and return AnalysisResult.
    """
    # Stage 1: Parse Resume
    parsed_resume = await parse_resume_text(raw_resume_text)

    # Stage 2: Evaluate ATS Score and Analyze Skill Gaps concurrently
    ats_score, skill_gap = await asyncio.gather(
        evaluate_ats_score(parsed_resume, job_description),
        analyze_skill_gaps(parsed_resume, job_description)
    )

    # Stage 3: Rewrite Experience & Generate Interview Prep concurrently
    rewrite_report, interview_prep = await asyncio.gather(
        rewrite_resume(parsed_resume, job_description, skill_gap),
        generate_interview_prep(parsed_resume, job_description, skill_gap)
    )

    # Stage 4: Assemble final result
    return AnalysisResult(
        resume_data=parsed_resume,
        ats_score=ats_score,
        skill_gap=skill_gap,
        rewrite_report=rewrite_report,
        interview_prep=interview_prep
    )
