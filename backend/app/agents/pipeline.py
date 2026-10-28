"""Resumizer analysis pipeline.

Stage 1 (parallel): parse the resume · extract the job's requirements (separately)
Stage 2 (code):     score and gap-check — deterministic, every match cites resume text
Stage 3 (parallel): rewrite bullets · write interview questions

Every stage reports how it ran: "ai", "rule_based" (AI unavailable, text-grounded
fallback), "unavailable" (withheld rather than faked) or "failed".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from app.agents.interview_generator_agent import interview_with_ai, rule_based_questions
from app.agents.job_analysis_agent import analyze_job_with_ai, rule_based_requirements
from app.agents.resume_parser_agent import parse_resume_with_ai, rule_based_parse
from app.agents.resume_rewrite_agent import rewrite_with_ai
from app.agents.scoring import score_resume
from app.llm import AgentOutputError, ChatClient, ProviderError, get_client
from app.schemas.resume import AnalysisResult, InterviewPrepReport, ResumeRewriteReport, StageReport

log = logging.getLogger("resumizer.pipeline")

# Provider failures that will affect every call, so later stages skip the AI.
_FATAL = {"model_unavailable", "auth", "not_configured"}


class AnalysisUnavailable(Exception):
    """Reliable analysis can't be produced (AI down and the resume can't be read by rules)."""

    def __init__(self, message: str, reason: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.reason = reason or {}


def _why(e: Exception) -> str:
    if isinstance(e, ProviderError):
        return {
            "model_unavailable": "The AI model isn't available from the provider.",
            "auth": "The AI provider rejected the server's API key.",
            "not_configured": "The server has no AI provider key configured.",
            "rate_limited": "The AI provider's rate limit was reached.",
            "timeout": "The AI provider took too long to respond.",
            "network": "The server couldn't reach the AI provider.",
        }.get(e.kind, "The AI provider returned an error.")
    if isinstance(e, AgentOutputError):
        return "The AI's answer wasn't in a usable format."
    return "Unexpected error."


async def run_resumizer_pipeline(raw_resume_text: str, job_description: str, client: Optional[ChatClient] = None,
                                 clients: Optional[Dict[str, ChatClient]] = None) -> AnalysisResult:
    """`client` (tests) is used for every task; otherwise each task uses its own routed client."""
    clients = dict(clients or {})
    for task in ("analysis", "rewrite", "interview"):
        clients.setdefault(task, client or get_client(task))
    client = clients["analysis"]
    stages: Dict[str, StageReport] = {}
    warnings: List[str] = []
    first_error: Dict[str, Optional[ProviderError]] = {"e": None}

    def ai_down() -> bool:
        e = first_error["e"]
        return isinstance(e, ProviderError) and e.kind in _FATAL

    def note_error(stage: str, e: Exception):
        log.warning("Stage %s fell back: %s", stage, getattr(e, "message", str(e)))
        if isinstance(e, ProviderError) and first_error["e"] is None:
            first_error["e"] = e

    # ── Stage 1 ──
    async def parse():
        try:
            r, w, m = await parse_resume_with_ai(client, raw_resume_text)
            stages["parse"] = StageReport(status="ai", model=m)
            return r, w
        except (ProviderError, AgentOutputError) as e:
            note_error("parse", e)
            r, w = rule_based_parse(raw_resume_text)
            stages["parse"] = StageReport(status="rule_based", message=_why(e))
            return r, w

    async def job():
        try:
            r, w, m = await analyze_job_with_ai(client, job_description)
            stages["job"] = StageReport(status="ai", model=m)
            return r, w
        except (ProviderError, AgentOutputError) as e:
            note_error("job", e)
            r, w = rule_based_requirements(job_description)
            stages["job"] = StageReport(status="rule_based", message=_why(e))
            return r, w

    (resume, w1), (reqs, w2) = await asyncio.gather(parse(), job())
    warnings += w1 + w2

    if stages["parse"].status != "ai" and not (resume.work_experience or resume.technical_skills):
        raise AnalysisUnavailable(
            "The AI is unavailable and your resume couldn't be read reliably without it, so no analysis was produced. Try again later.",
            first_error["e"].public() if first_error["e"] else None,
        )

    # ── Stage 2 ──
    method = "ai" if stages["job"].status == "ai" else "rule_based"
    ats, gap = score_resume(resume, raw_resume_text, reqs, method)
    stages["scoring"] = StageReport(status="rule_based", message="Scored in code from defined criteria.")

    # ── Stage 3 ──
    async def rewrite():
        if ai_down():
            stages["rewrite"] = StageReport(status="unavailable", message=_why(first_error["e"]) + " Rewrites need the AI, so none were produced.")
            return ResumeRewriteReport(), []
        try:
            r, w, m = await rewrite_with_ai(clients["rewrite"], resume, raw_resume_text, job_description, ats.matched_keywords, ats.missing_keywords)
            stages["rewrite"] = StageReport(status="ai", model=m or None)
            return r, w
        except (ProviderError, AgentOutputError) as e:
            note_error("rewrite", e)
            stages["rewrite"] = StageReport(status="unavailable", message=_why(e) + " Rewrites need the AI, so none were produced.")
            return ResumeRewriteReport(), []

    async def interview():
        if not ai_down():
            try:
                r, w, m = await interview_with_ai(clients["interview"], resume, raw_resume_text, reqs, ats.matched_keywords, ats.missing_keywords)
                if r.questions:
                    stages["interview"] = StageReport(status="ai", model=m)
                    return r, w
            except (ProviderError, AgentOutputError) as e:
                note_error("interview", e)
        r, w = rule_based_questions(resume, reqs, ats.matched_keywords, ats.missing_keywords)
        stages["interview"] = StageReport(status="rule_based", message=_why(first_error["e"]) if first_error["e"] else "The AI didn't return usable questions.")
        return r, w

    (rewrites, w3), (prep, w4) = await asyncio.gather(rewrite(), interview())
    warnings += w3 + w4

    ai_stages = [stages[k].status for k in ("parse", "job", "rewrite", "interview")]
    status = "complete" if all(s == "ai" for s in ai_stages) else "unavailable" if not any(s == "ai" for s in ai_stages) else "partial"

    return AnalysisResult(
        status=status, stages=stages, warnings=warnings, job_requirements=reqs, resume_data=resume,
        ats_score=ats, skill_gap=gap, rewrite_report=rewrites, interview_prep=prep,
    )
