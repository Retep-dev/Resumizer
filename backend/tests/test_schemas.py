from app.schemas.resume import (
    ResumeSchema,
    WorkExperience,
    ATSScore,
    SkillGapReport,
    ResumeRewriteReport,
    BulletPointRewrite,
    WorkExperienceRewrite,
    InterviewPrepReport,
    InterviewQuestion,
    AnalysisResult,
)


def test_schema_instantiation():
    resume = ResumeSchema(
        full_name="Jane Doe",
        email="jane@example.com",
        technical_skills=["Python", "FastAPI", "React"],
        work_experience=[
            WorkExperience(
                company="Tech Corp",
                job_title="Software Engineer",
                bullet_points=["Built REST APIs with Python"]
            )
        ]
    )
    assert resume.full_name == "Jane Doe"
    assert len(resume.technical_skills) == 3

    ats = ATSScore(
        overall_score=85,
        keyword_match_score=80,
        experience_match_score=90,
        formatting_score=85,
        breakdown_summary="Strong profile match for Senior Software Engineer.",
        matched_keywords=["Python", "FastAPI"],
        missing_keywords=["Docker"]
    )
    assert ats.overall_score == 85

    skill_gap = SkillGapReport(
        matched_hard_skills=["Python", "FastAPI"],
        missing_hard_skills=["Kubernetes"],
        priority_skill_recommendations=["Add Docker and Kubernetes containerization experience"]
    )
    assert "Kubernetes" in skill_gap.missing_hard_skills

    rewrite = ResumeRewriteReport(
        tailored_summary="Results-driven Engineer with expertise in Python & React.",
        rewritten_experiences=[
            WorkExperienceRewrite(
                company="Tech Corp",
                job_title="Software Engineer",
                rewritten_bullets=[
                    BulletPointRewrite(
                        original_bullet="Built REST APIs",
                        rewritten_bullet="Engineered high-throughput REST APIs using FastAPI, scaling user traffic by 40%.",
                        star_action="Engineered FastAPI endpoints",
                        star_result="Scaled traffic by 40%",
                        added_keywords=["FastAPI", "REST API"]
                    )
                ]
            )
        ]
    )
    assert len(rewrite.rewritten_experiences[0].rewritten_bullets) == 1

    interview = InterviewPrepReport(
        questions=[
            InterviewQuestion(
                question_type="technical",
                question="How do you handle async request bottlenecks in FastAPI?",
                context_or_reason="Role emphasizes high-concurrency Python backend services.",
                star_guide="Describe a time you benchmarked async routes.",
                sample_answer="I used asyncio gather and profiled database queries."
            )
        ]
    )
    assert interview.questions[0].question_type == "technical"

    full_analysis = AnalysisResult(
        resume_data=resume,
        ats_score=ats,
        skill_gap=skill_gap,
        rewrite_report=rewrite,
        interview_prep=interview
    )
    assert full_analysis.ats_score.overall_score == 85


if __name__ == "__main__":
    test_schema_instantiation()
    print("All Pydantic schema tests passed successfully!")
