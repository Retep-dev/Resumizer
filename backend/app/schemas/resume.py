from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = Field(description="Company or organization name")
    job_title: str = Field(description="Job title or role")
    location: Optional[str] = Field(default=None, description="City, State/Country or Remote")
    start_date: Optional[str] = Field(default=None, description="Start date")
    end_date: Optional[str] = Field(default=None, description="End date or Present")
    bullet_points: List[str] = Field(default_factory=list, description="Achievements and responsibilities bullet points")


class Education(BaseModel):
    institution: str = Field(description="University or institution name")
    degree: str = Field(description="Degree name e.g., Bachelor of Science")
    field_of_study: Optional[str] = Field(default=None, description="Field of study or major")
    graduation_year: Optional[str] = Field(default=None, description="Graduation year")


class Project(BaseModel):
    name: str = Field(description="Project title")
    description: str = Field(description="Brief overview of project")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    link: Optional[str] = Field(default=None, description="Repository or live URL")


class ResumeSchema(BaseModel):
    full_name: str = Field(description="Candidate's full name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="City, State/Country")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github: Optional[str] = Field(default=None, description="GitHub profile URL")
    summary: Optional[str] = Field(default=None, description="Professional summary or objective statement")
    technical_skills: List[str] = Field(default_factory=list, description="Programming languages, frameworks, hard technical skills")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills e.g., Leadership, Communication")
    tools_and_frameworks: List[str] = Field(default_factory=list, description="Tools, platforms, software e.g., Git, Docker, AWS")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="Work history")
    education: List[Education] = Field(default_factory=list, description="Educational background")
    certifications: List[str] = Field(default_factory=list, description="Certifications and licenses")
    projects: List[Project] = Field(default_factory=list, description="Notable projects")


class ATSScore(BaseModel):
    overall_score: int = Field(description="Overall ATS match percentage from 0 to 100")
    keyword_match_score: int = Field(description="Keyword alignment score from 0 to 100")
    experience_match_score: int = Field(description="Experience & role alignment score from 0 to 100")
    formatting_score: int = Field(description="ATS structure and readability score from 0 to 100")
    breakdown_summary: str = Field(description="Executive summary explaining the scores")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords present in both resume and JD")
    missing_keywords: List[str] = Field(default_factory=list, description="Critical keywords in JD missing from resume")


class SkillGapReport(BaseModel):
    matched_hard_skills: List[str] = Field(default_factory=list, description="Hard skills matched")
    missing_hard_skills: List[str] = Field(default_factory=list, description="Required hard skills missing from candidate resume")
    matched_soft_skills: List[str] = Field(default_factory=list, description="Soft skills matched")
    missing_soft_skills: List[str] = Field(default_factory=list, description="Required soft skills missing from candidate resume")
    priority_skill_recommendations: List[str] = Field(default_factory=list, description="Top skills to acquire/highlight immediately")


class BulletPointRewrite(BaseModel):
    original_bullet: str = Field(description="Original resume bullet point")
    rewritten_bullet: str = Field(description="Optimized bullet point incorporating metrics and keywords")
    star_action: str = Field(description="Action taken (STAR formula)")
    star_result: str = Field(description="Quantifiable impact/result (STAR formula)")
    added_keywords: List[str] = Field(default_factory=list, description="JD keywords injected into rewritten bullet")


class WorkExperienceRewrite(BaseModel):
    company: str
    job_title: str
    rewritten_bullets: List[BulletPointRewrite]


class ResumeRewriteReport(BaseModel):
    tailored_summary: str = Field(description="High-impact professional summary tailored specifically to target job description")
    rewritten_experiences: List[WorkExperienceRewrite] = Field(default_factory=list, description="Tailored experience sections")


class InterviewQuestion(BaseModel):
    question_type: str = Field(description="Type of question: behavioral, technical, or gap_focused")
    question: str = Field(description="The interview question")
    context_or_reason: str = Field(description="Why this question is likely to be asked based on candidate's background/gaps")
    star_guide: str = Field(description="Guidance on how candidate should structure their answer using STAR")
    sample_answer: str = Field(description="High-scoring response model")


class InterviewPrepReport(BaseModel):
    questions: List[InterviewQuestion] = Field(default_factory=list, description="Custom generated interview questions")


class AnalysisResult(BaseModel):
    resume_data: ResumeSchema
    ats_score: ATSScore
    skill_gap: SkillGapReport
    rewrite_report: ResumeRewriteReport
    interview_prep: InterviewPrepReport
