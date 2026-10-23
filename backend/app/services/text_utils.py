"""Deterministic text helpers used to ground AI output in the uploaded resume.

Everything here is pure Python with no AI involved, so the checks behave the
same on every run and can be unit-tested.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable, List, Optional, Set

_STOPWORDS = {
    "a", "an", "and", "or", "the", "of", "in", "on", "for", "to", "with", "at", "by", "as", "is",
    "be", "are", "experience", "skills", "skill", "knowledge", "strong", "proven", "ability", "using",
}

_BULLET_CHARS = "•●▪◦‣∙·*–—-"


def normalize(text: str) -> str:
    """Unicode-normalise, unify dashes/quotes/bullets and collapse whitespace."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace(" ", " ").replace("​", "")
    t = re.sub(r"[‐‑‒–—―]", "-", t)
    t = re.sub(r"[‘’‚′]", "'", t)
    t = re.sub(r"[“”„″]", '"', t)
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _stem(token: str) -> str:
    t = token.lower()
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if len(t) > len(suffix) + 2 and t.endswith(suffix):
            return t[: -len(suffix)]
    return t


def _tokens(text: str) -> List[str]:
    # Keep tech tokens like c#, c++, node.js, a/b, ci/cd intact.
    return re.findall(r"[a-z0-9][a-z0-9#+./]*[a-z0-9#+]|[a-z0-9]", normalize(text).lower())


def _significant(tokens: Iterable[str]) -> List[str]:
    return [t for t in tokens if t not in _STOPWORDS]


def term_in_text(term: str, text: str) -> bool:
    """True if a skill/keyword is supported by the text.

    A term matches when its normalised form appears verbatim, or when every
    significant token of the term (stemmed) appears on the same line.
    """
    if not term or not text:
        return False
    nterm = normalize(term).lower().strip()
    ntext = normalize(text).lower()
    if len(nterm) <= 3 or re.fullmatch(r"[a-z0-9#+./]+", nterm):
        # Short or single tokens must match as whole words (avoid "go" in "google").
        return re.search(r"(?<![a-z0-9])" + re.escape(nterm) + r"(?![a-z0-9])", ntext) is not None
    if nterm in ntext:
        return True
    want = [_stem(t) for t in _significant(_tokens(nterm))]
    if not want:
        return False
    # Every word of the term must appear close together (within a short window),
    # so "data modeling" doesn't match "usage data ... retention modeling".
    window = len(want) + 2
    for line in ntext.splitlines():
        stems = [_stem(t) for t in _tokens(line)]
        positions = {w: [i for i, s in enumerate(stems) if s == w] for w in set(want)}
        if any(not p for p in positions.values()):
            continue
        anchor = want[0]
        for start in positions[anchor]:
            if all(any(abs(i - start) < window for i in positions[w]) for w in positions):
                return True
    return False


def evidence_for(term: str, text: str, max_len: int = 160) -> Optional[str]:
    """Return the resume line that supports a term, trimmed for display."""
    for line in normalize(text).splitlines():
        if line.strip() and term_in_text(term, line):
            s = line.strip().lstrip(_BULLET_CHARS + " ")
            return s if len(s) <= max_len else s[: max_len - 1] + "…"
    return None


_NUM_RE = re.compile(r"(?<![a-z])\$?\d+(?:[.,]\d+)*(?:\s?%|x|k|m|bn)?", re.IGNORECASE)


def numbers_in(text: str) -> Set[str]:
    """Numeric claims in a string, normalised (e.g. '35%', '14', '$2.5m')."""
    out = set()
    for m in _NUM_RE.finditer(normalize(text or "")):
        out.add(re.sub(r"\s+", "", m.group(0).lower()).replace(",", ""))
    return out


def unsupported_numbers(candidate: str, *sources: str) -> Set[str]:
    """Numbers in `candidate` that don't appear anywhere in the sources.

    Bare digits are compared without unit so '14 tests' supports '14'.
    """
    allowed = set()
    for s in sources:
        for n in numbers_in(s):
            allowed.add(n)
            allowed.add(re.sub(r"[%xkm$]|bn", "", n))
    bad = set()
    for n in numbers_in(candidate):
        core = re.sub(r"[%xkm$]|bn", "", n)
        if n not in allowed and core not in allowed:
            bad.add(n)
    return bad


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_month_year(value: Optional[str], today: Optional[date] = None) -> Optional[date]:
    """Parse '2021', 'Mar 2021', '03/2021', 'Present' into a date (first of month)."""
    if not value:
        return None
    v = normalize(value).strip().lower()
    today = today or date.today()
    if v in {"present", "current", "now", "today", "ongoing"}:
        return date(today.year, today.month, 1)
    m = re.search(r"(\d{1,2})[/.-](\d{4})", v)
    if m and 1 <= int(m.group(1)) <= 12:
        return date(int(m.group(2)), int(m.group(1)), 1)
    m = re.search(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", v)
    if m and m.group(1) in _MONTHS:
        return date(int(m.group(2)), _MONTHS[m.group(1)], 1)
    m = re.search(r"(19|20)\d{2}", v)
    if m:
        return date(int(m.group(0)), 1, 1)
    return None


def years_between(start: Optional[str], end: Optional[str], today: Optional[date] = None) -> Optional[float]:
    s = parse_month_year(start, today)
    e = parse_month_year(end or "present", today)
    if not s or not e or e < s:
        return None
    return round((e.year - s.year) + (e.month - s.month) / 12, 1)


def required_years(job_description: str) -> Optional[int]:
    """Smallest 'N+ years' requirement stated in a job description."""
    found = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?years?", normalize(job_description).lower())]
    found = [n for n in found if 0 < n <= 30]
    return min(found) if found else None


def word_tokens_overlap(a: str, b: str) -> float:
    """Share of significant stemmed tokens of `a` present in `b` (0..1)."""
    want = {_stem(t) for t in _significant(_tokens(a))}
    if not want:
        return 0.0
    have = {_stem(t) for t in _tokens(b)}
    return len(want & have) / len(want)
