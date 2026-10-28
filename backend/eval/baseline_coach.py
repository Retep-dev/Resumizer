"""FROZEN BASELINE: the coach as deployed at commit 5187a28, for before/after comparison only."""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

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


_REWRITE_RE = re.compile(r"\b(rewrite|re-write|reword|rephrase|improve|strengthen|tighten|polish|redo|edit)\b", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^\s*[•●▪◦‣∙·*\-–—]\s*(.+)$")
_GENERIC = {"bullet", "bullets", "point", "line", "rewrite", "stronger", "better", "this", "that", "make", "more", "with",
            "from", "into", "them", "their", "your", "mine", "about", "please", "role", "resume", "job", "posting", "for",
            "the", "and", "can", "you", "could", "would", "should", "impactful", "improve", "strengthen"}


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z0-9+#.]*|\d+", normalize(text).lower()) if (len(w) >= 4 or w.isdigit()) and w not in _GENERIC}


def resume_bullets(resume_text: Optional[str], analysis: dict) -> List[str]:
    bullets = [b for j in ((analysis or {}).get("resume_data") or {}).get("work_experience", []) or [] for b in j.get("bullet_points", []) or []]
    if not bullets and resume_text:
        bullets = [m.group(1).strip() for line in resume_text.splitlines() if (m := _BULLET_LINE.match(line))]
    return [b for b in bullets if b.strip()]


def target_bullets(message: str, bullets: List[str]) -> List[str]:
    """The bullet(s) a rewrite request refers to, or [] if it isn't one."""
    if not _REWRITE_RE.search(message or "") or not bullets:
        return []
    want = _words(message)
    scored = [(len(want & _words(b)), b) for b in bullets]
    best = max((s for s, _ in scored), default=0)
    return [b for s, b in scored if s == best] if best else []


def rewrite_blocks(reply: str, targets: List[str]) -> List[str]:
    """The parts of a reply that are a new version of the target bullet(s).

    Paragraphs that mostly restate a target are rewrites; the target's exact
    text (a quoted original) and [bracketed suggestions] are removed, leaving
    whatever the coach changed or added.
    """
    target_words = set().union(*(_words(t) for t in targets)) if targets else set()
    if not target_words:
        return []
    out = []
    for para in re.split(r"\n\s*\n", normalize(reply or "")):
        if len(_words(para) & target_words) / len(target_words) < 0.4:
            continue
        rest = re.sub(r"\[[^\]]*\]", " ", para)
        for t in targets:
            rest = re.sub(re.escape(normalize(t).strip(" .")), " ", rest, flags=re.IGNORECASE)
        if _words(rest):
            out.append(rest)
    return out


def merged_bullets(reply: str, targets: List[str], bullets: List[str], message: str) -> List[str]:
    """Other bullets whose distinctive content shows up in a rewrite of the target."""
    blocks = rewrite_blocks(reply, targets)
    if not blocks:
        return []
    keep = set().union(*(_words(t) for t in targets)) | _words(message)
    got = set().union(*(_words(x) for x in blocks))
    out = []
    for b in bullets:
        if b in targets:
            continue
        distinctive = _words(b) - keep
        hits = distinctive & got
        if len(hits) >= 2 and len(hits) / max(len(distinctive), 1) >= 0.3:
            out.append(b)
    return out


_CLAIM_RE = re.compile(
    r"\b(I have (?:worked|used|built|run|deployed|managed|maintained|experience|started|completed|taken|been)|"
    r"I've (?:worked|used|built|run|deployed|managed|maintained|started|completed|taken|been)|"
    r"I worked|I used|I built|I deployed|I started|I completed|I'm (?:familiar|currently|learning|studying|taking|completing|working)|"
    r"I am (?:familiar|currently|learning|studying|taking|completing|working)|my experience (?:with|in|on))\b", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(haven't|have not|hasn't|not|never|no|don't|didn't|without|if you(?:'ve| have)?|if true)\b", re.IGNORECASE)


def claimed_missing(reply: str, missing: List[str], resume_text: str) -> List[str]:
    """Missing skills the reply puts in the candidate's mouth as experience they have."""
    from app.services.text_utils import term_in_text

    out = []
    for sentence in re.split(r"(?<=[.!?])[\"')\]]*\s+|[\"]\s*|\n+|\s+→\s+", normalize(reply or "")):
        # "I haven't used X, but I've been reading X docs": judge each clause on its own.
        for clause in re.split(r"\bbut\b|\bhowever\b|;", sentence, flags=re.IGNORECASE):
            if not _CLAIM_RE.search(clause) or _NEGATION_RE.search(clause):
                continue
            for k in missing:
                if k not in out and term_in_text(k, clause) and not term_in_text(k, resume_text or ""):
                    out.append(k)
    return out


def borrowed_from_posting(reply: str, targets: List[str], resume_text: str, job_description: str) -> List[str]:
    """Words in a rewritten bullet that come from the posting but not from the candidate's resume."""
    resume_words, job_words = _words(resume_text or ""), _words(job_description or "")
    target_words = set().union(*(_words(t) for t in targets)) if targets else set()
    borrowed = []
    for block in rewrite_blocks(reply, targets):
        for w in sorted(_words(block) - resume_words - target_words):
            if w in job_words and w not in borrowed:
                borrowed.append(w)
    return borrowed


async def _correct(client: ChatClient, messages: List[Dict[str, str]], draft: str, note: str):
    """Ask again with the faulty draft and the correction at the end, where the model attends most."""
    out = await client.complete(messages + [{"role": "assistant", "content": draft}, {"role": "user", "content": note}],
                                temperature=0.2, max_tokens=1200)
    # The user never saw the draft, so drop any "Corrected answer:" preamble.
    out.text = re.sub(r"^\s*[*_#\s]*(?:here(?:'s| is) (?:the|my) )?corrected (?:answer|rewrite|version|bullet)[*_\s]*:?[*_\s]*", "", out.text, flags=re.IGNORECASE)
    return out


def _phrases(text: str, words: List[str]) -> List[str]:
    """Whole phrases ('patient-facing') around the flagged words, for a readable note."""
    out = []
    for w in words:
        m = re.search(rf"[A-Za-z0-9-]*{re.escape(w)}[A-Za-z0-9-]*", normalize(text), re.IGNORECASE)
        p = m.group(0) if m else w
        if p.lower() not in (o.lower() for o in out):
            out.append(p)
    return out


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
    reply = completion.text

    # Suggested answers or bullets must not claim skills the resume doesn't show.
    missing = list(((analysis or {}).get("ats_score") or {}).get("missing_keywords") or [])
    grounding_text = resume_text or _resume_from_analysis(analysis)
    claimed = claimed_missing(reply, missing, grounding_text)
    if claimed:
        note = ("Please correct that: your draft suggested the candidate say they have experience with " + ", ".join(claimed)
                + ", which their resume doesn't show. Never script a claim of experience they don't have; suggest honest wording instead. Give me just the corrected answer.")
        retry = await _correct(client, messages, reply, note)
        reply = retry.text
        still = claimed_missing(reply, missing, grounding_text)
        if still:
            reply += ("\n\nNote: your resume doesn't show " + ", ".join(still)
                      + ". Only say you've used it if that's true.")

    # Rewrite requests: make sure the coach didn't fold other bullets into the one asked about.
    bullets = resume_bullets(resume_text, analysis)
    targets = target_bullets(user_message, bullets)
    borrowed = borrowed_from_posting(reply, targets, grounding_text, job_description) if targets else []
    if borrowed:
        note = ("Please correct that: your rewrite took words from the job posting that describe work the candidate didn't do ("
                + ", ".join(borrowed) + "). Rewrite only " + " / ".join(f'"{t}"' for t in targets)
                + " using what that bullet says; mention the posting's terms only as a bracketed suggestion like \"[if true: ...]\". Give me just the corrected rewrite.")
        retry = await _correct(client, messages, reply, note)
        reply = retry.text
        still = borrowed_from_posting(reply, targets, grounding_text, job_description)
        if still:
            reply += ("\n\nNote: this suggestion uses wording from the job posting (" + ", ".join(f"“{p}”" for p in _phrases(reply, still))
                      + ") that your resume doesn't support. Only keep them if they describe what you actually did.")
    merged = merged_bullets(reply, targets, bullets, user_message) if targets else []
    if merged:
        note = ("Please correct that: rewrite only this bullet: " + " / ".join(f'"{t}"' for t in targets)
                + ". Do not include content from other bullets, such as: " + " / ".join(f'"{m}"' for m in merged)
                + ". Give me just the corrected answer.")
        retry = await _correct(client, messages, reply, note)
        if not merged_bullets(retry.text, targets, bullets, user_message):
            return retry.text
        reply = retry.text + ("\n\nNote: this suggestion includes details from another bullet (" + "; ".join(f"“{m}”" for m in merged)
                              + "). Only combine them if they really describe the same piece of work.")
    return reply


__all__ = ["chat_with_career_coach", "clean_history", "ProviderError"]
