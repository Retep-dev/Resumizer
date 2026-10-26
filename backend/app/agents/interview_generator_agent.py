"""Stage 3b — interview questions grounded in the resume and the posting."""
from __future__ import annotations

import json
import re
from typing import List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.llm import ChatClient, complete_json
from app.schemas.resume import InterviewPrepReport, InterviewQuestion, JobRequirements, ResumeSchema
from app.services.text_utils import normalize, term_in_text, unsupported_numbers

INTERVIEW_SYSTEM_PROMPT = """You are an experienced hiring manager preparing a candidate for an interview.

Write exactly 6 questions: 2 "behavioral", 2 "technical" (about skills the posting requires) and 2 "gap_focused" (about requirements missing from the resume).

For each question give:
- question_type: "behavioral" | "technical" | "gap_focused"
- question
- context_or_reason: why an interviewer would ask it, referring to the posting or the resume
- star_guide: how to structure the answer with Situation, Task, Action, Result, pointing to a specific role or bullet from the resume when one fits
- sample_answer: a model answer built ONLY from facts in the resume. Describe actions only at the level of detail the resume gives: if the resume says what was done but not how, write a placeholder such as "[how you did it]". Never name commands, functions, column or table names, configuration settings, tools or techniques the resume doesn't mention. Where the answer needs a detail the resume doesn't give, write a bracketed placeholder such as "[the number of users affected]" instead of inventing it. Only use digits that are copied from the resume; otherwise write a bracketed placeholder. Never invent numbers, employers, projects or tools. For gap questions, be honest that the candidate hasn't used the skill and focus on related experience from the resume.

Return one JSON object: {"questions": [ ... 6 objects ... ]}"""

_TYPES = {"behavioral", "technical", "gap_focused"}
_ALLCAPS_OK = {"STAR", "ATS", "CV", "UK", "US", "USA", "EU", "OK", "TBD"}


def unsupported_specifics(answer: str, allowed_text: str) -> Set[str]:
    """Concrete technical details in an answer that the allowed text doesn't contain.

    Catches what a number check can't: code (`...`), identifiers like
    shipment_id or trigger_rule=one_success, keywords like MERGE, and named
    tools from the skills vocabulary.
    """
    from app.agents.job_analysis_agent import HARD_SKILLS  # avoid import cycle

    if not answer:
        return set()
    allowed = normalize(allowed_text).lower()
    found = set()
    for code in re.findall(r"`([^`]+)`", answer):
        if code.strip().lower() not in allowed:
            found.add(code.strip())
    for tok in re.findall(r"\b[A-Za-z]+_[A-Za-z0-9_]+(?:=[A-Za-z0-9_]+)?\b|\b\w+\(\)", answer):
        if tok.lower() not in allowed:
            found.add(tok)
    for tok in re.findall(r"\b[A-Z]{3,}\b", answer):
        if tok not in _ALLCAPS_OK and not re.search(rf"(?<![a-z0-9]){re.escape(tok.lower())}(?![a-z0-9])", allowed):
            found.add(tok)
    for term in HARD_SKILLS:
        if term in ("R", "Go") or len(term) < 3:
            continue
        if term_in_text(term, answer) and not term_in_text(term, allowed_text):
            found.add(term)
    return found
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
        if answer and (unsupported_numbers(answer, resume_text) or unsupported_specifics(answer, resume_text + "\n" + q.question)):
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
    raw_answers = {q.question.strip(): q.sample_answer for q in report.questions}
    report, removed = validate_questions(report, resume_text)
    report, removed = await _repair_answers(client, report, raw_answers, resume_text, payload, removed)
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
    warnings = [f"{removed} sample answer(s) were removed because they included numbers or technical details that aren't in your resume."] if removed else []
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


class _Answer(BaseModel):
    question: str
    sample_answer: Optional[str] = None


class _Answers(BaseModel):
    answers: List[_Answer] = Field(default_factory=list)


async def _repair_answers(client: ChatClient, report: InterviewPrepReport, raw_answers: dict, resume_text: str,
                          payload: dict, removed: int) -> Tuple[InterviewPrepReport, int]:
    """Give the model one chance to rewrite answers that were removed, then re-check them."""
    problems = {}
    for q in report.questions:
        raw = raw_answers.get(q.question)
        if raw and not q.sample_answer:
            bad = sorted(unsupported_numbers(raw, resume_text)) + sorted(unsupported_specifics(raw, resume_text + "\n" + q.question))
            problems[q.question] = bad
    if not problems:
        return report, removed
    user = (f"Context (JSON):\n{json.dumps(payload, ensure_ascii=False)}\n\nThese sample answers used details that are not in the resume. "
            "Rewrite each answer using only facts from the resume, with bracketed placeholders like [how you did it] for anything the resume doesn't say.\n"
            + "\n".join(f"- Question: {q}\n  Details not in the resume: {', '.join(b)}" for q, b in problems.items())
            + '\n\nReturn one JSON object: {"answers": [{"question": str, "sample_answer": str}]}')
    try:
        fixed, _ = await complete_json(client, INTERVIEW_SYSTEM_PROMPT, user, _Answers, temperature=0.1, max_tokens=2500)
    except Exception:
        return report, removed
    by_q = {a.question.strip(): a.sample_answer for a in fixed.answers if a.sample_answer}
    out = []
    for q in report.questions:
        new = by_q.get(q.question)
        if q.question in problems and new and not unsupported_numbers(new, resume_text) and not unsupported_specifics(new, resume_text + "\n" + q.question):
            q = q.model_copy(update={"sample_answer": new.strip()})
            removed -= 1
        out.append(q)
    return InterviewPrepReport(questions=out), removed


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
