"""What a resume bullet states, and whether a rewrite still states only that.

Deterministic and model-free, so the same rewrite always gets the same verdict.
Used to accept or withhold rewrites, to label accepted ones ("keeps 9 → 2 per
month, Airflow, Snowflake"), and by the evaluation to audit any model's output.

A rewrite may change wording, order and emphasis. It may not:
  * add or change numbers, or what a number measures
  * add tools or skills (from the missing list or from elsewhere in the resume)
  * change the kind of work (maintained → built, helped → led, mentored → managed)
  * add outcomes or benefits the bullet doesn't state ("improving accuracy")
  * pull in facts from another bullet
[Bracketed placeholders] are questions for the candidate, so they're exempt from
the outcome and merge checks but not from the number and skill checks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from app.services.text_utils import normalize, numbers_in, term_in_text, unsupported_numbers

_IRREGULAR = {
    "built": "build", "rebuilt": "rebuild", "wrote": "write", "written": "write", "rewrote": "rewrite", "ran": "run",
    "led": "lead", "grew": "grow", "drove": "drive", "driven": "drive", "oversaw": "oversee", "overseen": "oversee",
    "taught": "teach", "made": "make", "kept": "keep", "sped": "speed", "cut": "cut", "set": "set", "won": "win",
    "brought": "bring", "began": "begin", "begun": "begin", "chose": "choose", "gave": "give", "held": "hold",
    "met": "meet", "sold": "sell", "spent": "spend", "took": "take", "thought": "think", "understood": "understand",
    "did": "do", "done": "do", "went": "go", "saw": "see", "found": "find", "told": "tell", "shut": "shut",
}

FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "for", "to", "with", "at", "by", "as", "from", "into",
    "per", "via", "through", "across", "behind", "within", "over", "under", "after", "before", "during", "about",
    "its", "their", "our", "my", "his", "her", "this", "that", "these", "those", "which", "who", "whom", "it",
    "is", "was", "were", "be", "been", "are", "s", "each", "every", "all", "both", "new", "up", "out", "while",
    "using", "used", "use", "than", "then", "so", "such", "also", "more", "most", "other", "own",
}

# Kinds of action. A rewrite must keep the original's main kind and must not add a stronger one.
VERB_KINDS: Dict[str, Set[str]] = {
    "create": {"build", "rebuild", "create", "develop", "design", "redesign", "ship", "launch", "implement", "write", "author",
               "introduce", "add", "establish", "engineer", "code", "produce", "make", "deliver", "set"},
    "maintain": {"maintain", "run", "operate", "monitor", "update", "fix", "troubleshoot", "debug", "keep", "administer", "service"},
    "lead": {"lead", "manage", "own", "head", "direct", "oversee", "spearhead", "drive", "champion", "supervise", "chair"},
    "help": {"help", "assist", "contribute", "participate"},
    "collaborate": {"work", "collaborate", "partner", "liaise", "coordinate", "cooperate"},
    "teach": {"mentor", "coach", "train", "teach", "onboard", "tutor", "educate", "guide"},
    "improve": {"reduce", "cut", "increase", "improve", "grow", "raise", "boost", "speed", "optimize", "optimise",
                "streamline", "lower", "double", "triple", "halve", "accelerate", "decrease", "expand", "shorten"},
    "analyze": {"analyze", "analyse", "research", "investigate", "measure", "evaluate", "test", "audit", "model", "assess", "review"},
    "organise": {"organise", "organize", "schedule", "plan", "arrange"},
    "respond": {"answer", "respond", "resolve", "handle"},
}
_KIND_OF = {}
for _k, _vs in VERB_KINDS.items():
    for _v in _vs:
        _KIND_OF[_v] = _k

# Kinds that claim more than others when introduced by a rewrite.
_ESCALATIONS = {"lead": "leadership", "create": "building something new", "improve": "a result"}

# Words that state an outcome, benefit or scope. Adding one the bullet doesn't support is an invented claim.
OUTCOME_WORDS = {
    "improve", "improvement", "increase", "boost", "save", "saving", "accuracy", "accurate", "reliability", "reliable",
    "efficiency", "efficient", "performance", "revenue", "profit", "profitability", "cost", "engagement", "conversion",
    "retention", "satisfaction", "productivity", "compliance", "compliant", "scalability", "scalable", "seo", "faster",
    "quicker", "streamline", "ensure", "enable", "empower", "stakeholder", "cross-functional", "end-to-end", "strategic",
    "award", "recognition", "promote", "hour", "manual", "impact", "impactful", "significant", "significantly", "robust",
    "seamless", "enterprise", "production-grade", "high-quality", "integrity", "growth", "decision-making", "insight",
    "visibility", "uptime", "availability", "secure", "security", "quality", "downstream", "data-driven", "kpi",
}


def lemma(word: str) -> str:
    w = word.lower().strip("'’")
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            w = w[: -len(suf)]
            if suf in ("ing", "ed") and len(w) > 3 and w[-1] == w[-2] and w[-1] not in "lsz":
                w = w[:-1]  # shipped → ship, running → run
            break
    if w.endswith("ie") and len(w) > 4:
        w = w[:-2] + "y"
    return w.rstrip("e") if len(w) > 4 else w


def _lemma_set(words: Iterable[str]) -> Set[str]:
    return {lemma(w) for w in words}


_VERB_LEMMAS = {lemma(v): k for v, k in _KIND_OF.items()}
_OUTCOME_LEMMAS = {lemma(w) for w in OUTCOME_WORDS}
_FUNCTION_LEMMAS = {lemma(w) for w in FUNCTION_WORDS}


def words(text: str, *, keep_brackets: bool = True) -> List[str]:
    t = normalize(text or "")
    if not keep_brackets:
        t = re.sub(r"\[[^\]]*\]", " ", t)
    return re.findall(r"[a-z][a-z0-9+#'’-]*", t.lower())


def placeholders(text: str) -> List[str]:
    return re.findall(r"\[([^\]]+)\]", text or "")


def verb_kinds(text: str) -> List[str]:
    """Kinds of action in the order they appear."""
    out = []
    for w in words(text, keep_brackets=False):
        k = _VERB_LEMMAS.get(lemma(w))
        if k and k not in out:
            out.append(k)
    return out


def _has_result(text: str) -> bool:
    t = normalize(text).lower()
    return "improve" in verb_kinds(text) or bool(re.search(r"\bfrom\s+\S+\s+(?:\w+\s+){0,3}to\s+\S+", t)) or bool(
        re.search(r"\d+\s*%|\b(?:doubl|tripl|halv)", t))


@dataclass
class BulletFacts:
    text: str
    numbers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    action: Optional[str] = None
    kinds: List[str] = field(default_factory=list)
    has_result: bool = False

    def summary(self) -> Dict[str, object]:
        return {"numbers": self.numbers, "tools": self.tools, "action": self.action, "states_a_result": self.has_result}


def extract_facts(bullet: str, known_skills: Iterable[str] = ()) -> BulletFacts:
    kinds = verb_kinds(bullet)
    return BulletFacts(
        text=bullet,
        numbers=sorted(numbers_in(bullet), key=lambda n: bullet.find(n)),
        tools=[k for k in dict.fromkeys(known_skills) if term_in_text(k, bullet)],
        action=kinds[0] if kinds else None,
        kinds=kinds,
        has_result=_has_result(bullet),
    )


def _number_context_problems(original: str, rewrite: str) -> List[str]:
    """Words right after a number say what it measures; they must come from the original."""
    orig = _lemma_set(words(original))
    toks = re.findall(r"\d+(?:[.,]\d+)?%?|[a-z][a-z'-]*", normalize(re.sub(r"\[[^\]]*\]", " ", rewrite)).lower())
    out = []
    for i, t in enumerate(toks):
        if not t[0].isdigit():
            continue
        content = [w for w in toks[i + 1:i + 4] if not w[0].isdigit() and lemma(w) not in _FUNCTION_LEMMAS][:1]
        if content and lemma(content[0]) not in orig:
            out.append(f"{t} {content[0]}")
    return out


def distinctive_words(text: str, exclude: Set[str]) -> Set[str]:
    return {lemma(w) for w in words(text, keep_brackets=False) if len(w) >= 4 and lemma(w) not in _FUNCTION_LEMMAS} - exclude


def verify_rewrite(original: str, rewrite: str, *, missing: Iterable[str] = (), known_skills: Iterable[str] = (),
                   other_bullets: Iterable[str] = ()) -> List[str]:
    """Reasons the rewrite says something the original doesn't (empty list = faithful)."""
    problems: List[str] = []
    missing, known_skills = list(missing), list(known_skills)

    bad = unsupported_numbers(rewrite, original)
    if bad:
        problems.append(f"added numbers that aren't in the original ({', '.join(sorted(bad))})")
    lost = [n for n in numbers_in(original) if n not in numbers_in(rewrite)]
    if lost:
        problems.append(f"dropped numbers from the original ({', '.join(lost)})")
    garbled = _number_context_problems(original, rewrite)
    if garbled:
        problems.append(f"changed what a number measures ({', '.join(garbled)})")

    claimed = [k for k in missing if term_in_text(k, rewrite) and not term_in_text(k, original)]
    if claimed:
        problems.append(f"claimed {', '.join(claimed)}, which your resume doesn't show")
    attributed = [k for k in known_skills if k not in claimed and term_in_text(k, rewrite) and not term_in_text(k, original)]
    if attributed:
        problems.append(f"attributed {', '.join(attributed)} to this bullet, which the original doesn't mention")
    dropped_tools = [k for k in known_skills if term_in_text(k, original) and not term_in_text(k, rewrite)]
    if dropped_tools:
        problems.append(f"dropped {', '.join(dropped_tools)} from the original")

    ok, nk = verb_kinds(original), verb_kinds(rewrite)
    if ok and ok[0] not in nk:
        problems.append(f"changed what you did (the original says you {ok[0].replace('analyze', 'analysed')}d it)"
                        if ok[0] in ("maintain",) else f"changed the kind of work (the original is about '{ok[0]}')")
    for k, what in _ESCALATIONS.items():
        if k in nk and k not in ok and not (k == "improve" and _has_result(original)) and not (k == "create" and ok and ok[0] == "create"):
            problems.append(f"turned it into {what} the original doesn't describe")

    orig_lemmas = _lemma_set(words(original))
    new_outcomes = sorted({w for w in words(rewrite, keep_brackets=False) if lemma(w) in _OUTCOME_LEMMAS and lemma(w) not in orig_lemmas})
    if new_outcomes:
        problems.append(f"added an outcome or claim the original doesn't state ({', '.join(new_outcomes)})")

    keep = distinctive_words(original, set())
    got = distinctive_words(rewrite, set())
    merged = []
    for other in other_bullets:
        if normalize(other).strip() == normalize(original).strip():
            continue
        d = distinctive_words(other, keep)
        hits = d & got
        if len(hits) >= 2 and len(hits) / max(len(d), 1) >= 0.3:
            merged.append(other)
    if merged:
        problems.append("merged in another bullet (" + "; ".join(f"“{m}”" for m in merged) + ")")
    return problems


def new_content_words(original: str, rewrite: str) -> List[str]:
    """Content words the rewrite adds (outside placeholders). An evaluation metric, not a verdict."""
    orig = _lemma_set(words(original))
    return sorted({w for w in words(rewrite, keep_brackets=False)
                   if lemma(w) not in orig and lemma(w) not in _FUNCTION_LEMMAS and lemma(w) not in _VERB_LEMMAS})


def verification_note(facts: BulletFacts) -> List[str]:
    """Plain-English list of what was checked, shown with an accepted rewrite."""
    notes = []
    if facts.numbers:
        notes.append("keeps " + ", ".join(facts.numbers))
    if facts.tools:
        notes.append("keeps " + ", ".join(facts.tools))
    notes.append("same kind of work" if facts.action else "no new actions")
    notes.append("no new tools, numbers or results")
    return notes
