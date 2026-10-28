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


def _best_overlap(text: str, targets: List[str]) -> float:
    """Share of the closest target bullet's words found in the text (per target, so two
    candidate targets don't dilute each other)."""
    w = _words(text)
    return max((len(w & _words(t)) / max(len(_words(t)), 1) for t in targets), default=0.0)


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
        if _best_overlap(para, targets) < 0.4:
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


_QUOTE_RE = re.compile(r"[“\"]([^”\"]{12,})[”\"]")
_COMMENTARY_RE = re.compile(r"\b(you|your|you're|you've)\b", re.IGNORECASE)
_IF_TRUE_RE = re.compile(r"\[\s*if true[^\]]*\]", re.IGNORECASE)


def bullet_segments(raw: str, bullet: str = "") -> List[str]:
    """Parts of a reply line that read as resume wording: quoted text, or the line itself when it isn't commentary.
    '[if true: …]' suggestions are allowed by design and removed before checking."""
    line = _IF_TRUE_RE.sub(" ", raw)
    quoted = [q.strip() for q in _QUOTE_RE.findall(normalize(line)) if len(q.split()) >= 4]
    if quoted:
        return [_clean_line(q) for q in quoted]
    clean = _clean_line(line)
    if not clean or _COMMENTARY_RE.search(clean):
        return []
    if bullet and len(clean.split()) > 2 * len(bullet.split()) + 10:
        return []
    return [clean]


def rewrite_problems(reply: str, targets: List[str], ledger: Ledger, known: List[str], bullets: List[str],
                     resume_text: str, job_description: str) -> List[Problem]:
    """Verify every quoted or bullet-like line that is a version of the requested bullet, exactly as rewrites are verified."""
    out = []
    if not targets:
        return out
    missing = [m for m in ledger.missing if m not in ledger.may_claim()]
    for raw in normalize(reply or "").splitlines():
        for line in bullet_segments(raw, max(targets, key=len)):
            if _best_overlap(line, targets) < 0.4:
                continue
            target = max(targets, key=lambda t: len(_words(t) & _words(line)))
            if " ".join(line.lower().split()).strip(" .") == " ".join(target.lower().split()).strip(" ."):
                continue  # the original quoted as-is
            problems = verify_rewrite(target, line, missing=missing, known_skills=known, other_bullets=bullets)
            borrowed = borrowed_from_posting(line, [target], resume_text, job_description)
            if borrowed:
                problems.append("uses the posting's wording for work the bullet doesn't describe ("
                                + ", ".join(f"“{p}”" for p in phrases(line, borrowed)) + ")")
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


# ── Broader claim check: any first- or second-person experience claim the resume doesn't support ──

_CLAIM_VERB_RE = re.compile(
    r"\b(?:i|i've|i have|i had|i'm|i am|we|we've|you've|you have)\b(?:\s+[a-z'’-]+){0,3}?\s+"
    r"(worked|work|used|use|built|build|written|wrote|write|begun|began|started|completed|deployed|deploy|explored|exploring|"
    r"learned|studied|done|created|managed|manage|led|lead|run|ran|set up|configured|implemented|developed|handled|owned|own|"
    r"delivered|maintained|treat|comfortable|familiar|experienced|proficient)\b", re.IGNORECASE)
_HEDGE_CLAUSE_RE = re.compile(r"\b(if|whether|unless|only if|haven't|have not|hasn't|not|never|no|don't|didn't|without|"
                              r"aren't|isn't|wasn't|would|could|might|plan to|want to|ready to|eager to|keen to|happy to)\b", re.IGNORECASE)
_GENERIC_CLAIM = {
    "comfortable", "ready", "quickly", "learn", "concept", "role", "team", "work", "experience", "skill", "tool", "years",
    "project", "company", "environment", "hands-on", "apply", "able", "focus", "today", "week", "month", "currently",
    "already", "approach", "mindset", "process", "daily", "core", "same", "similar", "related", "direct", "directly",
    "really", "always", "often", "every", "end-to-end", "level", "detail", "part", "side", "real", "solid", "strong",
    "good", "great", "well", "things", "much", "many", "most", "also", "some", "your", "this", "that", "these", "there",
    "here", "them", "they", "what", "which", "while", "where", "when", "into", "onto", "from", "with", "have", "been",
    "enthusiasm", "expertise", "deeper", "developing", "interest", "eager", "excited", "passion", "growth", "opportunity",
    "being", "were", "will", "just", "even", "only", "about", "across", "each", "other", "than", "then", "very",
}


_COMMON_WORD_TOOLS = {"express", "spring", "swift", "ruby", "rust", "go", "r", "security", "statistics", "retention", "regression",
                      "forecasting", "experimentation", "agile", "accessibility", "prototyping", "budgeting", "accounting",
                      "storytelling", "presentation", "leadership", "communication", "retail"}


def unsupported_claims(reply: str, ledger: Ledger, resume_text: str, user_text: str = "") -> List[Problem]:
    """Claims of experience ("I've written Terraform scripts", "you have managed larger operations") whose
    specifics aren't in the resume or in what the candidate said. Conditional or negated clauses are allowed."""
    from app.agents.bullet_facts import FUNCTION_WORDS
    from app.agents.interview_generator_agent import unsupported_specifics

    allowed = resume_text + "\n" + user_text
    allowed_lemmas = {lemma(w) for w in re.findall(r"[a-z][a-z0-9+#'’-]*", normalize(allowed).lower())}
    out = []
    sents, skip_next = [], False
    for line in normalize(reply or "").splitlines():
        if not line.strip():
            continue
        if re.search(r"\b(don'?t|do not|avoid|never|what not to|instead of)\b", line, re.IGNORECASE) and len(line.split()) <= 12:
            skip_next = True  # a short "Don't say:" cue: the example under it is what NOT to claim
            continue
        if skip_next:
            skip_next = False
            continue
        sents += sentences(line)
    for s in sents:
        for clause in re.split(r"\bbut\b|\bhowever\b|;|—|–|:|\(", s, flags=re.IGNORECASE):
            low = normalize(clause).lower()
            if not _CLAIM_VERB_RE.search(low) or _HEDGE_CLAUSE_RE.search(low):
                continue
            specifics = sorted(x for x in unsupported_specifics(clause, allowed)
                               if x in clause and x.lower() not in _COMMON_WORD_TOOLS)
            content = sorted({w for w in re.findall(r"[a-z][a-z0-9+#.-]*", re.sub(r"\[[^\]]*\]", " ", low))
                              if len(w) >= 4 and lemma(w) not in allowed_lemmas and w not in _GENERIC_CLAIM
                              and lemma(w) not in _GENERIC_CLAIM and w not in FUNCTION_WORDS})
            if specifics or len(content) >= 3:
                what = ", ".join(specifics) if specifics else ", ".join(content[:4])
                out.append(Problem("claim", s, f"claims experience your resume doesn't show ({what})"))
                break
    return out


def silent_rewrites(reply: str, bullets: List[str], ledger: Ledger, known: List[str], resume_text: str,
                    job_description: str, skip_targets: List[str]) -> List[Problem]:
    """Quoted or bullet-like lines that restate a resume bullet with changes, in answers not asking for a rewrite."""
    out = []
    missing = [m for m in ledger.missing if m not in ledger.may_claim()]
    for raw in normalize(reply or "").splitlines():
        for line in bullet_segments(raw):
            if skip_targets and _best_overlap(line, skip_targets) >= 0.4:
                continue  # a version of the requested bullet: rewrite_problems judges it
            scored = [(len(_words(line) & _words(b)) / max(len(_words(b)), 1), b) for b in bullets if b not in skip_targets]
            if not scored:
                continue
            ov, bullet = max(scored)
            if ov < 0.6 or len(line.split()) > 1.6 * len(bullet.split()) + 8:
                continue
            if " ".join(line.lower().split()).strip(" .") == " ".join(bullet.lower().split()).strip(" ."):
                continue
            # In passing mentions, shortening (dropping a number) isn't a fabrication; adding things is.
            problems = [p for p in verify_rewrite(bullet, line, missing=missing, known_skills=known, other_bullets=bullets)
                        if not p.startswith("dropped numbers")]
            if problems:
                out.append(Problem("rewrite", line, "; ".join(problems), bullet))
    return out


