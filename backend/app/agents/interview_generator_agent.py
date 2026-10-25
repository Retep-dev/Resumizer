"""Stage 3b — interview questions grounded in the resume and the posting."""
from __future__ import annotations

import json
from typing import List, Tuple

from app.llm import ChatClient, complete_json
from app.schemas.resume import InterviewPrepReport, InterviewQuestion, JobRequirements, ResumeSchema
from app.services.text_utils import unsupported_numbers

INTERVIEW_SYSTEM_PROMPT = """You are an experienced hiring manager preparing a candidate for an interview.

Write exactly 6 questions: 2 "behavioral", 2 "technical" (about skills the posting requires) and 2 "gap_focused" (about requirements missing from the resume).

For each question give:
- question_type: "behavioral" | "technical" | "gap_focused"
- question
- context_or_reason: why an interviewer would ask it, referring to the posting or the resume
- star_guide: how to structure the answer with Situation, Task, Action, Result, pointing to a specific role or bullet from the resume when one fits
- sample_answer: a model answer built ONLY from facts in the resume. Where the answer needs a detail the resume doesn't give, write a bracketed placeholder such as "[the number of users affected]" instead of inventing it. Only use digits that are copied from the resume; otherwise write a bracketed placeholder. Never invent numbers, employers, projects or tools. For gap questions, be honest that the candidate hasn't used the skill and focus on related experience from the resume.

Return one JSON object: {"questions": [ ... 6 objects ... ]}"""

_TYPES = {"behavioral", "technical", "gap_focused"}
_STAR = "Situation: set the scene in one sentence. Task: what you were responsible for. Action: what you did, in order. Result: what changed — use a real number if you have one."


def validate_questions(report: InterviewPrepReport, resume_text: str) -> Tuple[InterviewPrepReport, int]:
    """Normalise types and drop sample answers that contain invented numbers."""
    removed = 0
    out = []
    for q in report.questions:
        qt = q.question_type.strip().lower().replace("-", "_").replace(" ", "_")
        qt = "behavioral" if qt.startswith("behav") else "gap_focused" if qt.startswith("gap") else qt
        if qt not in _TYPES or not q.question.strip():
            continue
        answer = q.sample_answer
        if answer and unsupported_numbers(answer, resume_text):
            answer = None
            removed += 1
        out.append(InterviewQuestion(question_type=qt, question=q.question.strip(), context_or_reason=q.context_or_reason,
                                     star_guide=q.star_guide or _STAR, sample_answer=answer))
    return InterviewPrepReport(questions=out[:8]), removed


async def interview_with_ai(client: ChatClient, resume: ResumeSchema, resume_text: str, reqs: JobRequirements,
                            matched: List[str], missing: List[str]) -> Tuple[InterviewPrepReport, List[str], str]:
    payload = {
        "resume": json.loads(resume.model_dump_json(exclude={"email", "phone", "linkedin", "github"})),
        "posting_title": reqs.title,
        "requirements_found_in_resume": matched,
        "requirements_missing_from_resume": missing,
    }
    report, model = await complete_json(
        client, INTERVIEW_SYSTEM_PROMPT, f"Context (JSON):\n{json.dumps(payload, ensure_ascii=False)}", InterviewPrepReport,
        temperature=0.3, max_tokens=4000,
    )
    report, removed = validate_questions(report, resume_text)
    if len(report.questions) < 4:
        # One more attempt for a full set.
        retry, _ = await complete_json(
            client, INTERVIEW_SYSTEM_PROMPT,
            f"Context (JSON):\n{json.dumps(payload, ensure_ascii=False)}\n\nYour last reply had only {len(report.questions)} usable question(s). Return all 6.",
            InterviewPrepReport, temperature=0.3, max_tokens=4000,
        )
        retry, removed2 = validate_questions(retry, resume_text)
        if len(retry.questions) > len(report.questions):
            report, removed = retry, removed2
    warnings = [f"{removed} sample answer(s) were removed because they included numbers that aren't in your resume."] if removed else []
    if 0 < len(report.questions) < 4:
        # Top up with template questions for the types the AI didn't cover, labelled as such.
        have = {q.question_type for q in report.questions}
        extra, _ = rule_based_questions(resume, reqs, matched, missing)
        added = [q for q in extra.questions if q.question_type not in have][: 6 - len(report.questions)]
        report = InterviewPrepReport(questions=report.questions + added)
        if added:
            warnings.append(f"The AI returned only a few questions, so {len(added)} template question(s) from the posting were added (no sample answers).")
    if not report.questions:
        warnings.append("The AI didn't return usable interview questions.")
    return report, warnings, model


def rule_based_questions(resume: ResumeSchema, reqs: JobRequirements, matched: List[str], missing: List[str]) -> Tuple[InterviewPrepReport, List[str]]:
    """Honest, template questions from the posting — no sample answers."""
    qs: List[InterviewQuestion] = []
    latest = resume.work_experience[0] if resume.work_experience else None
    if latest and (latest.job_title or latest.company):
        where = " at ".join(x for x in (latest.job_title, latest.company) if x)
        qs.append(InterviewQuestion(question_type="behavioral", question=f"Walk us through your work as {where}. What are you most proud of?",
                                    context_or_reason="Interviewers usually start with your most recent role.", star_guide=_STAR))
    qs.append(InterviewQuestion(question_type="behavioral", question="Tell us about a time you disagreed with a colleague or stakeholder. How did you resolve it?",
                                context_or_reason="A common question for judging collaboration.", star_guide=_STAR))
    for k in matched[:2]:
        qs.append(InterviewQuestion(question_type="technical", question=f"The role uses {k}. Walk us through a specific piece of work where you used it.",
                                    context_or_reason=f"{k} is in the posting and on your resume.", star_guide=_STAR))
    for k in missing[:2]:
        qs.append(InterviewQuestion(question_type="gap_focused", question=f"This role needs {k}. What's your experience with it, and how would you get up to speed?",
                                    context_or_reason=f"{k} is in the posting but not on your resume.",
                                    star_guide="Be honest about your level. Point to the closest related experience on your resume, then give a concrete plan for learning it."))
    return InterviewPrepReport(questions=qs), ["Interview questions were generated from templates because the AI was unavailable; no sample answers are included."]
