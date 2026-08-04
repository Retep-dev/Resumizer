import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.resume import ResumeSchema, WorkExperience, SkillGapReport
from app.agents.interview_generator_agent import generate_interview_prep


async def main():
    resume = ResumeSchema(
        full_name="Alex Smith",
        technical_skills=["React", "JavaScript", "HTML", "CSS"],
        work_experience=[
            WorkExperience(
                company="FootPrint",
                job_title="Frontend Developer (React)",
                bullet_points=["Built user interfaces using React"]
            )
        ]
    )
    
    jd = """
    We are looking for a Senior Fullstack Engineer in Lagos.
    Requirements:
    - 4+ years of React experience.
    - Experience with microservices architecture and C# / .NET.
    - Golang experience is a plus.
    - Sample React project and C# project required.
    """

    skill_gap = SkillGapReport(
        matched_hard_skills=["React", "JavaScript"],
        missing_hard_skills=["Microservices", "C#", ".NET", "Golang"],
        priority_skill_recommendations=["Build C# sample project", "Learn microservices concepts"]
    )

    print("Testing generate_interview_prep agent...")
    try:
        res = await generate_interview_prep(resume, jd, skill_gap)
        print(f"Result type: {type(res)}")
        print(f"Raw Result dict: {res.model_dump()}")
        print(f"Number of questions generated: {len(res.questions)}")
        for idx, q in enumerate(res.questions):
            print(f"\nQuestion #{idx+1} [{q.question_type}]: {q.question}")
    except Exception as e:
        import traceback
        print("ERROR running generate_interview_prep:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
