"""Deterministic checks on coach replies. Each returns what's wrong, so it can be fixed or removed."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.agents.bullet_facts import lemma, verify_rewrite
from app.agents.coach_evidence import Ledger
from app.services.text_utils import normalize, term_in_text

_REWRITE_RE = re.compile(r"\b(rewrite|re-write|reword|rephrase|improve|strengthen|tighten|polish|redo|edit)\b", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^\s*[•●▪◦‣∙·*\-–—]\s*(.+)$")
_GENERIC = {"bullet", "bullets", "point", "line", "rewrite", "stronger", "better", "this", "that", "make", "more", "with",
            "from", "into", "them", "their", "your", "mine", "about", "please", "role", "resume", "job", "posting", "for",
            "the", "and", "can", "you", "could", "would", "should", "impactful", "improve", "strengthen"}


def _words(text: str) -> set:
    """Content words as lemmas, so 'scheduled' and 'scheduling' count as the same word."""
    return {w if w.isdigit() else lemma(w) for w in re.findall(r"[a-z][a-z0-9+#.]*|\d+", normalize(text).lower())
            if (len(w) >= 4 or w.isdigit()) and w not in _GENERIC}


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




# ── New checks ──

@dataclass
class Problem:
    kind: str          # claim | listing | rewrite
    text: str          # the sentence or line that's wrong (normalised)
    detail: str        # plain-English reason
    target: Optional[str] = None  # original bullet, for rewrite problems


_ADD_RE = re.compile(r"\b(add|list|include|put|mention|highlight|feature)\b", re.IGNORECASE)
_WHERE_RE = re.compile(r"(skills?\b|resume|\bcv\b|profile|summary|bullet|professional development|experience section)", re.IGNORECASE)
_COND_RE = re.compile(r"\b(if (?:you|true|you've|you have|that's true|it's true|so)|only if|unless|once you|after you|when you(?:'ve| have)?)\b", re.IGNORECASE)
_DONT_RE = re.compile(r"\b(don't|do not|doesn't|does not|isn't|is not|never|avoid|instead of|rather than|leave (?:it|them) off|not)\b", re.IGNORECASE)
_FAMILIAR_RE = r"(?:familiar with|proficient in|experienced (?:with|in)|knowledge of|exposure to|self-studied|working knowledge of|hands-on)"
_LEARNING_SECTION_RE = re.compile(r"\b(course|training|certificat\w*|project|learning|education)\b", re.IGNORECASE)


def sentences(text: str) -> List[str]:
    out = []
    for line in normalize(text or "").splitlines():
        out += [s for s in re.split(r"(?<=[.!?])[\"')\]]*\s+", line) if s.strip()]
    return out


def listing_advice(reply: str, ledger: Ledger) -> List[Problem]:
    """Advice to put a missing skill on the resume, or resume wording that implies it, without a 'only if true' condition."""
    out = []
    allowed = ledger.may_claim()
    for s in sentences(reply):
        for skill in ledger.missing:
            if skill in allowed or not term_in_text(skill, s) or _COND_RE.search(s):
                continue
            course_ok = ledger.said_in_chat.get(skill) == "course_or_project" and _LEARNING_SECTION_RE.search(s)
            implied = re.search(rf"{re.escape(skill)}\s*[:–—-]\s*{_FAMILIAR_RE}|{_FAMILIAR_RE}[^.]{{0,40}}{re.escape(skill)}", s, re.IGNORECASE)
            advises = _ADD_RE.search(s) and _WHERE_RE.search(s) and not _DONT_RE.search(s)
            if (advises or implied) and not course_ok:
                out.append(Problem("listing", s, f"suggests showing {skill} on your resume, which it doesn't support"))
                break
    return out


def scripted_claims(reply: str, ledger: Ledger, resume_text: str) -> List[Problem]:
    missing = [m for m in ledger.missing if m not in ledger.may_claim()]
    out = []
    for s in sentences(reply):
        claimed = claimed_missing(s, missing, resume_text)
        if claimed:
            out.append(Problem("claim", s, f"implies experience with {', '.join(claimed)}, which your resume doesn't show"))
    return out


_LINE_PREFIX = re.compile(r"^\s*(?:[-*•→>]+\s*|\d+[.)]\s*|\*\*[^*]{0,40}\*\*\s*:?\s*|(?:option \d+|rewrite|rewritten|new version|stronger version|version \d+|safe|strong|suggested|after)\s*[:—-]\s*)+", re.IGNORECASE)


def _clean_line(line: str) -> str:
    t = _LINE_PREFIX.sub("", normalize(line)).strip()
    t = t.strip("*_\"' ")
    return t


def rewrite_problems(reply: str, targets: List[str], ledger: Ledger, known: List[str], bullets: List[str],
                     resume_text: str, job_description: str) -> List[Problem]:
    """Verify every line that is a version of the requested bullet, exactly as rewrites are verified."""
    out = []
    if not targets:
        return out
    target_words = set().union(*(_words(t) for t in targets))
    for raw in normalize(reply or "").splitlines():
        line = _clean_line(raw)
        if not line or len(_words(line) & target_words) / max(len(target_words), 1) < 0.4:
            continue
        target = max(targets, key=lambda t: len(_words(t) & _words(line)))
        if " ".join(line.lower().split()).strip(" .") == " ".join(target.lower().split()).strip(" ."):
            continue  # the original quoted as-is
        missing = [m for m in ledger.missing if m not in ledger.may_claim()]
        problems = verify_rewrite(target, line, missing=missing, known_skills=known, other_bullets=bullets)
        borrowed = borrowed_from_posting(line, [target], resume_text, job_description)
        if borrowed:
            problems.append("uses the posting's wording for work the bullet doesn't describe (" + ", ".join(f"“{p}”" for p in phrases(line, borrowed)) + ")")
        if problems:
            out.append(Problem("rewrite", line, "; ".join(problems), target))
    return out


def phrases(text: str, words: List[str]) -> List[str]:
    """Whole phrases ('patient-facing') around flagged words, for a readable message."""
    out = []
    for w in words:
        m = re.search(rf"[A-Za-z0-9-]*{re.escape(w)}[A-Za-z0-9-]*", normalize(text), re.IGNORECASE)
        p = m.group(0) if m else w
        if p.lower() not in (o.lower() for o in out):
            out.append(p)
    return out
