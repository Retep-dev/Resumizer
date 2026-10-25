"""Career coach: multi-turn chat grounded in the candidate's real analysis."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from app.llm import ChatClient, ProviderError, get_client

MAX_TURNS = 12
MAX_MESSAGE_CHARS = 4000

COACH_SYSTEM_PROMPT = """You are a practical, honest career coach helping one candidate apply for one job.

You have the candidate's resume, the job description, and an analysis of how they match. Use them as your only source of facts about the candidate.

Rules:
- Refer to specific roles, bullets and requirements from the material below.
- Never say or imply the candidate has a skill, tool, metric or experience that isn't in the resume. If the resume doesn't show something, say so and suggest how they could honestly address it.
- Never advise adding a skill or tool to the resume that the candidate hasn't used — not even as "familiar with" or "eager to learn". For missing skills, suggest how to talk about them honestly in a cover letter or interview, or how to gain them.
- Never invent numbers. If a stronger bullet needs a metric, ask the candidate for it or use a bracketed placeholder like [number].
- When you rewrite a bullet, rewrite only that bullet: keep its facts, don't merge in other bullets, and don't add responsibilities, collaborators, outcomes or tools it doesn't mention. If adding something would help, show it as a bracketed suggestion the candidate must confirm, e.g. "[if true: with the analytics team]".
- If a question needs information you don't have, say what's missing.
- Be concise and use short bullet lists where they help.

=== RESUME ===
{resume}

=== JOB DESCRIPTION ===
{job}

=== ANALYSIS ===
{analysis}"""


def _analysis_digest(analysis: dict) -> str:
    """Compact, model-friendly summary of the analysis the user is looking at."""
    if not analysis:
        return "(not available)"
    ats = analysis.get("ats_score") or {}
    gap = analysis.get("skill_gap") or {}
    digest = {
        "status": analysis.get("status"),
        "overall_score": ats.get("overall_score"),
        "score_criteria": [{k: c.get(k) for k in ("name", "score", "detail")} for c in ats.get("criteria", [])],
        "keywords_found": ats.get("matched_keywords", []),
        "keywords_missing": ats.get("missing_keywords", []),
        "missing_hard_skills": gap.get("missing_hard_skills", []),
        "missing_soft_skills": gap.get("missing_soft_skills", []),
        "recommendations": gap.get("priority_skill_recommendations", []),
    }
    return json.dumps(digest, ensure_ascii=False)


def _resume_from_analysis(analysis: dict) -> str:
    r = (analysis or {}).get("resume_data") or {}
    return json.dumps({k: r.get(k) for k in ("full_name", "summary", "technical_skills", "tools_and_frameworks", "soft_skills",
                                                "work_experience", "education", "certifications", "projects")}, ensure_ascii=False)


def clean_history(chat_history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """Keep well-formed user/assistant turns, most recent MAX_TURNS, trimmed."""
    out = []
    for m in chat_history or []:
        role = (m or {}).get("role")
        content = (m or {}).get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            out.append({"role": role, "content": content.strip()[:MAX_MESSAGE_CHARS * 2]})
    # Conversations should alternate; drop a leading assistant turn (the UI greeting).
    while out and out[0]["role"] == "assistant":
        out.pop(0)
    return out[-MAX_TURNS:]


async def chat_with_career_coach(
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]],
    resume_text: Optional[str],
    job_description: str,
    analysis: dict,
    client: Optional[ChatClient] = None,
) -> str:
    client = client or get_client()
    system = COACH_SYSTEM_PROMPT.format(
        resume=(resume_text or _resume_from_analysis(analysis))[:12000],
        job=(job_description or "(not available)")[:8000],
        analysis=_analysis_digest(analysis),
    )
    messages = [{"role": "system", "content": system}] + clean_history(chat_history) + [
        {"role": "user", "content": user_message.strip()[:MAX_MESSAGE_CHARS]}
    ]
    completion = await client.complete(messages, temperature=0.4, max_tokens=1200)
    return completion.text


__all__ = ["chat_with_career_coach", "clean_history", "ProviderError"]
