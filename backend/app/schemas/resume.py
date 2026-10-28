from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ───────────────────────── Resume (source of truth) ─────────────────────────

class WorkExperience(BaseModel):
    company: str = Field(default="", description="Company or organization name, exactly as written")
    job_title: str = Field(default="", description="Job title, exactly as written")
    location: Optional[str] = Field(default=None, description="City, State/Country or Remote")
    start_date: Optional[str] = Field(default=None, description="Start date as written")
    end_date: Optional[str] = Field(default=None, description="End date as written, or Present")
    bullet_points: List[str] = Field(default_factory=list, description="Bullet points copied from the resume")


class Education(BaseModel):
    institution: str = Field(default="", description="University or institution name")
    degree: str = Field(default="", description="Degree name as written")
    field_of_study: Optional[str] = Field(default=None, description="Field of study or major")
    graduation_year: Optional[str] = Field(default=None, description="Graduation year")


class Project(BaseModel):
    name: str = Field(default="", description="Project title")
    description: str = Field(default="", description="Brief overview of project")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    link: Optional[str] = Field(default=None, description="Repository or live URL")


class ResumeSchema(BaseModel):
    full_name: str = Field(default="", description="Candidate's full name")
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    tools_and_frameworks: List[str] = Field(default_factory=list)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)


# ───────────────────────── Job description (analysed separately) ─────────────────────────

class JobRequirement(BaseModel):
    term: str = Field(description="Skill, tool or qualification named in the job description")
    category: Literal["hard", "soft"] = "hard"
    importance: Literal["required", "preferred"] = "required"
    aliases: List[str] = Field(default_factory=list, description="Common alternative spellings")


class JobRequirements(BaseModel):
    title: Optional[str] = None
    min_years: Optional[int] = None
    requirements: List[JobRequirement] = Field(default_factory=list)


# ───────────────────────── Scoring ─────────────────────────

class ScoreCriterion(BaseModel):
    name: str
    score: int = Field(description="0-100")
    weight: float = Field(description="Share of the overall score, 0-1")
    detail: str


class KeywordEvidence(BaseModel):
    keyword: str
    importance: Literal["required", "preferred"] = "required"
    found: bool
    evidence: Optional[str] = Field(default=None, description="Resume line that contains the keyword")


class ATSScore(BaseModel):
    overall_score: int = Field(description="Overall ATS match percentage from 0 to 100")
    keyword_match_score: int
    experience_match_score: int
    formatting_score: int
    breakdown_summary: str
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    criteria: List[ScoreCriterion] = Field(default_factory=list)
    keyword_evidence: List[KeywordEvidence] = Field(default_factory=list)
    method: str = Field(default="rule_based", description="How requirements were extracted: ai or rule_based")


class SkillGapReport(BaseModel):
    matched_hard_skills: List[str] = Field(default_factory=list)
    missing_hard_skills: List[str] = Field(default_factory=list)
    matched_soft_skills: List[str] = Field(default_factory=list)
    missing_soft_skills: List[str] = Field(default_factory=list)
    priority_skill_recommendations: List[str] = Field(default_factory=list)
    method: str = "rule_based"


# ───────────────────────── Rewrites ─────────────────────────

class BulletPointRewrite(BaseModel):
    original_bullet: str
    rewritten_bullet: str
    star_action: str = ""
    star_result: str = ""
    added_keywords: List[str] = Field(default_factory=list, description="Posting keywords that the original bullet already supports")
    needs_confirmation: List[str] = Field(default_factory=list, description="Questions for the candidate, e.g. a metric to add")
    status: Literal["rewritten", "kept_original"] = "rewritten"
    note: Optional[str] = None
    checks: List[str] = Field(default_factory=list, description="What was verified against the original, in plain English")

    @field_validator("star_action", "star_result", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return "" if v is None else v

    @field_validator("added_keywords", "needs_confirmation", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return [] if v is None else v


class WorkExperienceRewrite(BaseModel):
    company: str = ""
    job_title: str = ""
    rewritten_bullets: List[BulletPointRewrite] = Field(default_factory=list)


class ResumeRewriteReport(BaseModel):
    tailored_summary: Optional[str] = None
    rewritten_experiences: List[WorkExperienceRewrite] = Field(default_factory=list)


# ───────────────────────── Interview ─────────────────────────

class InterviewQuestion(BaseModel):
    question_type: str = Field(description="behavioral, technical, or gap_focused")
    question: str
    context_or_reason: str = ""
    star_guide: str = ""
    sample_answer: Optional[str] = None


class InterviewPrepReport(BaseModel):
    questions: List[InterviewQuestion] = Field(default_factory=list)


# ───────────────────────── Processing status ─────────────────────────

StageStatus = Literal["ai", "rule_based", "unavailable", "failed"]


class StageReport(BaseModel):
    status: StageStatus
    model: Optional[str] = None
    message: Optional[str] = None


class AnalysisResult(BaseModel):
    # "complete": every AI stage succeeded. "partial": some stages fell back to
    # rule-based output or were withheld. "unavailable": no AI stage succeeded;
    # only rule-based, text-grounded results are included.
    status: Literal["complete", "partial", "unavailable"] = "complete"
    stages: Dict[str, StageReport] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    job_requirements: Optional[JobRequirements] = None
    resume_data: ResumeSchema
    ats_score: ATSScore
    skill_gap: SkillGapReport
    rewrite_report: ResumeRewriteReport
    interview_prep: InterviewPrepReport
