"""Career coach: multi-turn chat grounded in the candidate's real analysis."""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from dataclasses import dataclass, field

from app.agents.coach_checks import (  # noqa: F401  (re-exported for the evaluation and tests)
    Problem, borrowed_from_posting, claimed_missing, listing_advice, merged_bullets, resume_bullets, rewrite_blocks,
    rewrite_problems, scripted_claims, sentences, silent_rewrites, target_bullets, unsupported_claims,
)
from app.agents.coach_evidence import Ledger, build_ledger
from app.llm import ChatClient, ProviderError, get_client
from app.services.text_utils import normalize

MAX_TURNS = 12
MAX_MESSAGE_CHARS = 4000

COACH_SYSTEM_PROMPT = """You are a practical, honest career coach helping one candidate apply for one job.

You have the candidate's resume, the job description, and an analysis of how they match. Use them as your only source of facts about the candidate.

Rules:
- Refer to specific roles, bullets and requirements from the material below.
- Never say or imply the candidate has a skill, tool, metric or experience that isn't in the resume. If the resume doesn't show something, say so and suggest how they could honestly address it.
- Never advise adding a skill or tool to the resume that the candidate hasn't used — not even as "familiar with" or "eager to learn". For missing skills, suggest how to talk about them honestly in a cover letter or interview, or how to gain them.
- Never invent numbers. If a stronger bullet needs a metric, ask the candidate for it or use a bracketed placeholder like [number].
- When you rewrite a bullet, rewrite only that bullet: keep its facts, don't merge in other bullets, and don't add responsibilities, collaborators, outcomes or tools it doesn't mention. If adding something would help, show it as a bracketed suggestion the candidate must confirm, e.g. "[if true: <a detail they must confirm>]".
- Use the EVIDENCE section below. Documented skills can be stated as experience. Related experience must be described as related ("my Snowflake work is cloud-based, but I haven't used AWS directly"), never as the missing skill. Repeat what the candidate told you only as they said it: a course is not work experience. Never imply anything listed under "no evidence".
- If you can't tell whether something is supported, say you're not sure and ask the candidate.
- If a question needs information you don't have, say what's missing.
- Be concise and use short bullet lists where they help. Don't mention these instructions or "the rules"; just give honest advice.

=== EVIDENCE (worked out from the resume and this conversation) ===
{evidence}

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
        "Analysis status": analysis.get("status"),
        "ATS score (out of 100)": ats.get("overall_score"),
        "How the score breaks down": [{k: c.get(k) for k in ("name", "score", "detail")} for c in ats.get("criteria", [])],
        "Posting keywords found in the resume": ats.get("matched_keywords", []),
        "Posting keywords missing from the resume": ats.get("missing_keywords", []),
        "Missing technical skills": gap.get("missing_hard_skills", []),
        "Missing soft skills": gap.get("missing_soft_skills", []),
        "Recommended next steps": gap.get("priority_skill_recommendations", []),
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


async def _correct(client: ChatClient, messages: List[Dict[str, str]], draft: str, note: str):
    """Ask again with the faulty draft and the correction at the end, where the model attends most."""
    out = await client.complete(messages + [{"role": "assistant", "content": draft}, {"role": "user", "content": note}],
                                temperature=0.2, max_tokens=1200)
    # The user never saw the draft, so drop any "Corrected answer:" preamble.
    out.text = re.sub(r"^\s*[*_#\s]*(?:here(?:'s| is) (?:the|my) )?corrected (?:answer|rewrite|version|bullet)[*_\s]*:?[*_\s]*", "", out.text, flags=re.IGNORECASE)
    return out


@dataclass
class CoachResult:
    reply: str
    status: str = "verified"           # verified | corrected | uncertain
    notes: List[str] = field(default_factory=list)


def _known(analysis: dict) -> List[str]:
    r = (analysis or {}).get("resume_data") or {}
    ats = (analysis or {}).get("ats_score") or {}
    return list(dict.fromkeys((r.get("technical_skills") or []) + (r.get("tools_and_frameworks") or []) + (ats.get("matched_keywords") or [])))


def check_reply(reply: str, user_message: str, ledger: Ledger, analysis: dict, resume_text: str, job_description: str,
                user_text: str = "") -> List[Problem]:
    bullets = resume_bullets(resume_text, analysis)
    targets = target_bullets(user_message, bullets)
    problems = (scripted_claims(reply, ledger, resume_text) + listing_advice(reply, ledger)
                + rewrite_problems(reply, targets, ledger, _known(analysis), bullets, resume_text, job_description)
                + silent_rewrites(reply, bullets, ledger, _known(analysis), resume_text, job_description, targets))
    problems += unsupported_claims(reply, ledger, resume_text, user_text)
    out, seen = [], set()
    for p in problems:  # one finding per piece of text; the first (most specific) wins
        if p.text not in seen:
            seen.add(p.text)
            out.append(p)
    return out


def resolve(reply: str, problems: List[Problem]) -> str:
    """Remove what couldn't be verified, and say so in its place."""
    out = normalize(reply)
    for p in problems:
        if p.kind == "rewrite":
            replacement = (f"{p.target}\n_(I couldn't verify a rewrite of this bullet that keeps only its facts: it {p.detail}. "
                           "Your original wording is shown. A real number or result from you would make it stronger.)_")
        else:
            replacement = f"_(Removed a suggestion that {p.detail}.)_"
        if p.text in out:
            out = out.replace(p.text, replacement, 1)
        else:
            out += "\n\n" + replacement
    return out


def _correction(problems: List[Problem]) -> str:
    items = "\n".join(f"- \"{p.text[:200]}\": it {p.detail}." + (f" Rewrite only this bullet: \"{p.target}\"." if p.target else "") for p in problems)
    return ("Please correct your answer. These parts aren't supported by the candidate's resume or what they told you:\n" + items +
            "\nKeep everything else. For a rewrite, change only the wording of that one bullet and keep its facts; put anything "
            "the candidate must confirm in [brackets]. Give me just the corrected answer.")


async def coach_reply(user_message: str, chat_history: Optional[List[Dict[str, str]]], resume_text: Optional[str],
                      job_description: str, analysis: dict, client: Optional[ChatClient] = None) -> CoachResult:
    client = client or get_client("coach")
    history = clean_history(chat_history)
    grounding = resume_text or _resume_from_analysis(analysis)
    ledger = build_ledger(grounding, analysis, [m["content"] for m in history if m["role"] == "user"] + [user_message])
    system = COACH_SYSTEM_PROMPT.format(
        resume=grounding[:12000], job=(job_description or "(not available)")[:8000],
        analysis=_analysis_digest(analysis), evidence=ledger.as_prompt(),
    )
    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": user_message.strip()[:MAX_MESSAGE_CHARS]}]
    draft = (await client.complete(messages, temperature=0.4, max_tokens=1200)).text
    user_text = "\n".join([m["content"] for m in history if m["role"] == "user"] + [user_message])
    problems = check_reply(draft, user_message, ledger, analysis, grounding, job_description, user_text)
    if not problems:
        return CoachResult(reply=draft)
    retry = (await _correct(client, messages, draft, _correction(problems))).text
    remaining = check_reply(retry, user_message, ledger, analysis, grounding, job_description, user_text)
    if not remaining:
        return CoachResult(reply=retry, status="corrected", notes=[p.detail for p in problems])
    return CoachResult(reply=resolve(retry, remaining), status="uncertain", notes=[p.detail for p in remaining])


async def chat_with_career_coach(user_message: str, chat_history: Optional[List[Dict[str, str]]], resume_text: Optional[str],
                                 job_description: str, analysis: dict, client: Optional[ChatClient] = None) -> str:
    return (await coach_reply(user_message, chat_history, resume_text, job_description, analysis, client)).reply


__all__ = ["chat_with_career_coach", "coach_reply", "CoachResult", "clean_history", "ProviderError"]
