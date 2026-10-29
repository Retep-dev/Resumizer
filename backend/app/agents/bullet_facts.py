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
    "maintain": {"maintain", "operate", "monitor", "update", "fix", "troubleshoot", "debug", "keep", "administer", "service"},
    "deliver": {"run", "conduct", "deliver", "execute", "host", "hold", "facilitate", "present", "teach-session"},
    "lead": {"lead", "manage", "own", "head", "direct", "oversee", "spearhead", "drive", "champion", "supervise", "chair"},
    "help": {"help", "assist", "contribute", "participate"},
    "collaborate": {"work", "collaborate", "partner", "liaise", "coordinate", "cooperate"},
    "teach": {"mentor", "coach", "train", "teach", "onboard", "tutor", "educate", "guide"},
    "improve": {"reduce", "cut", "increase", "improve", "grow", "raise", "boost", "optimize", "optimise",
                "streamline", "lower", "double", "triple", "halve", "accelerate", "decrease", "expand", "shorten"},
    "analyze": {"analyze", "analyse", "research", "investigate", "measure", "evaluate", "test", "audit", "model", "assess", "review"},
    "organise": {"organise", "organize", "schedule", "plan", "arrange"},
    "respond": {"answer", "respond", "resolve", "handle"},
}
_KIND_OF = {}
for _k, _vs in VERB_KINDS.items():
    for _v in _vs:
        _KIND_OF[_v] = _k

_KIND_PHRASE = {
    "create": "built or created something", "maintain": "maintained something", "lead": "led", "help": "helped",
    "collaborate": "worked with others", "teach": "mentored or trained people", "improve": "improved a result",
    "analyze": "analysed or reviewed something", "organise": "organised something", "respond": "handled requests",
    "deliver": "ran or delivered something",
}

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
    "highlight", "trend", "actionable", "valuable", "critical", "key", "result", "outcome", "success", "successful",
    "effectively", "efficiently", "best-in-class", "world-class",
}
_HEDGE_RE = r"(?:around|about|approximately|approx\.?|roughly|nearly|almost|up to|over|more than|some|circa|~)\s*"


_WORD_NUM = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
    "eighteen nineteen twenty".split())}
_WORD_NUM.update({"thirty": "30", "forty": "40", "fifty": "50", "hundred": "100", "dozen": "12", "half": "0.5", "double": "2"})


def word_numbers(text: str) -> Dict[str, str]:
    """Numbers written as words ('two junior engineers'), outside placeholders. 'one' as a pronoun is excluded."""
    t = re.sub(r"\[[^\]]*\]", " ", normalize(text or "")).lower()
    out = {}
    for m in re.finditer(r"\b(" + "|".join(k for k in _WORD_NUM if k not in ("half", "double", "one")) + r")\b", t):
        out[m.group(1)] = _WORD_NUM[m.group(1)]
    return out


def lemma(word: str) -> str:
    w = word.lower().strip("'’")
    if w in _IRREGULAR:
        w = _IRREGULAR[w]
    else:
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
    """Kinds of action in the order they appear. Only words in verb positions count (the opening word,
    words after to/and/by/then/while or a comma, -ed/-ing forms, and the first action word found), so
    'engineers' isn't read as 'engineer'."""
    out = []
    toks = re.findall(r"[a-z][a-z'’-]*|,", normalize(re.sub(r"\[[^\]]*\]", " ", text or "")).lower())
    prev = None
    for i, w in enumerate(toks):
        if w == ",":
            prev = w
            continue
        verb_slot = not out or i == 0 or prev in {"to", "and", "by", "then", "while", ","} or w.endswith("ed") or w.endswith("ing")
        k = _VERB_LEMMAS.get(lemma(w)) if verb_slot else None
        if k and k not in out:
            out.append(k)
        prev = w
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


# ── Meaning checks: who did what with whom, how much of it, when, and what came of it ──

# Words that set up a relationship between the candidate and other people. Introducing one the original
# doesn't have changes who did what ("sat with new agents on calls" → "shadowed calls" reverses who watched).
_RELATION_GROUPS = {
    "observing someone else's work": r"\bshadow\w*|\bobserv\w*|\bsat in on\b|\bsit in on\b",
    "working under someone": r"\bunder (?:the )?(?:supervision|guidance|direction)\b|\bsupervised by\b|\breport(?:ed|ing|s)? to\b|\bmentored by\b|\btrained by\b|\bcoached by\b",
    "acting on someone's behalf": r"\bon behalf of\b",
}
# Words that make the candidate's part bigger than the original says.
_SCOPE_UP = r"\b(?:independently|single-handedly|singlehandedly|solely|sole|alone|by myself|on my own|from scratch|end-to-end|entire|entirely|all|every|full|fully|company-wide|organization-wide|organisation-wide|whole)\b"
# Words that say the work was shared or partial. If the original has one, the rewrite must keep one.
_SHARED = r"\b(?:team|teams|group|alongside|jointly|together|co-\w+|colleagues?|assist\w*|support\w*|contribut\w*|participat\w*|part of|help(?:ed|ing|s)?\b(?!\s+(?:centre|center|desk|line|page|articles?|docs?|content)))\b"
# Qualifiers that limit a claim: plans, attempts, targets and estimates are not results.
_QUALIFIERS = r"\b(?:plan\w*|propos\w*|recommend\w*|suggest\w*|pilot\w*|draft\w*|trial\w*|attempt\w*|tried|try|aim\w*|goal|target\w*|expected|projected|estimated|forecast\w*|partial\w*|partly|nominated|shortlisted|finalist|runner-up|in progress|ongoing|working on|initial|prototype\w*)\b"
# Recurring periods. Changing one changes the chronology ("weekly reports" → "daily reports").
_PERIODS = {"day": r"\bdaily\b|\bper day\b|\ba day\b|\beach day\b|\bevery day\b|\bdays?\b",
            "week": r"\bweekly\b|\bweeks?\b", "month": r"\bmonthly\b|\bmonths?\b", "quarter": r"\bquarterly\b|\bquarters?\b",
            "year": r"\byearly\b|\bannual\w*\b|\byears?\b", "night": r"\bnightly\b|\bnights?\b|\bovernight\b",
            "hour": r"\bhourly\b|\bhours?\b", "shift": r"\bshifts?\b"}
# Results and recognition. Dropping one loses an accomplishment the candidate has.
_ACCOMPLISHMENTS = {"award", "recognition", "recognised", "recognized", "promote", "praise", "commend", "select", "win", "won",
                    "certify", "record", "rank", "exceed", "surpass", "achieve", "save", "satisfaction", "revenue", "profit",
                    "accuracy", "retention", "conversion", "uptime", "productivity", "efficiency", "compliance", "growth"}
_ACCOMPLISHMENT_LEMMAS = {lemma(w) for w in _ACCOMPLISHMENTS}


def _plain(text: str) -> str:
    return normalize(re.sub(r"\[[^\]]*\]", " ", text or "")).lower()


def meaning_problems(original: str, rewrite: str) -> List[str]:
    """Changes of meaning that keep every fact word-for-word but still misdescribe the work."""
    o, r = _plain(original), _plain(rewrite)
    out = []
    for what, pat in _RELATION_GROUPS.items():
        if re.search(pat, r) and not re.search(pat, o):
            out.append(f"changed who did what (it now describes {what})")
    passive = (r"\b(?:was|were|been|being|is|are|got)\s+(?:\w+ly\s+)?\w+(?:ed|ght|en|wn)\s+by\b|"
               r"\b(?:mentored|trained|coached|supervised|managed|led|taught|guided|assisted|supported|directed|overseen|hired|chosen|selected|assigned)\s+by\b")
    if re.search(passive, o) and not re.search(passive, r):
        out.append("changed who did what (the original says someone else did it to or for you)")
    up = sorted({m.group(0) for m in re.finditer(_SCOPE_UP, r)} - {m.group(0) for m in re.finditer(_SCOPE_UP, o)})
    if up:
        out.append(f"made your part bigger than the original says ({', '.join(up)})")
    if re.search(_SHARED, o) and not re.search(_SHARED, r):
        out.append("dropped that this was shared or team work")
    lost_q = sorted({m.group(0) for m in re.finditer(_QUALIFIERS, o)} - {m.group(0) for m in re.finditer(_QUALIFIERS, r)})
    if lost_q and not any(re.search(rf"\b{re.escape(lemma(q))}", r) for q in lost_q):
        out.append(f"dropped a qualifier that limits the claim ({', '.join(lost_q)})")
    op = {k for k, pat in _PERIODS.items() if re.search(pat, o)}
    rp = {k for k, pat in _PERIODS.items() if re.search(pat, r)}
    added, gone = sorted(rp - op), sorted(op - rp)
    if added and gone:
        out.append(f"changed the timeframe ({', '.join(gone)} → {', '.join(added)})")
    elif added:
        out.append(f"added a time detail the original doesn't give ({', '.join(added)})")
    elif gone:
        out.append(f"dropped a time detail from the original ({', '.join(gone)})")
    ol = {lemma(w) for w in words(original, keep_brackets=False)}
    rl = {lemma(w) for w in words(rewrite, keep_brackets=False)}
    lost_a = sorted((ol & _ACCOMPLISHMENT_LEMMAS) - rl)
    if lost_a:
        out.append(f"dropped a result the original states ({', '.join(lost_a)})")
    return out


def verify_rewrite(original: str, rewrite: str, *, missing: Iterable[str] = (), known_skills: Iterable[str] = (),
                   other_bullets: Iterable[str] = ()) -> List[str]:
    """Reasons the rewrite says something the original doesn't (empty list = faithful)."""
    problems: List[str] = []
    missing, known_skills = list(missing), list(known_skills)

    bad = set(unsupported_numbers(rewrite, original)) - set(word_numbers(original).values())
    if bad:
        problems.append(f"added numbers that aren't in the original ({', '.join(sorted(bad))})")
    lost = [n for n in numbers_in(original) if n not in numbers_in(rewrite)]
    if lost:
        problems.append(f"dropped numbers from the original ({', '.join(lost)})")
    hedged = [m.group(1) for m in re.finditer(rf"{_HEDGE_RE}(\$?\d[\d,.]*%?)", normalize(original), re.IGNORECASE)]
    made_exact = [n for n in hedged if n in rewrite and not re.search(rf"{_HEDGE_RE}{re.escape(n)}", normalize(rewrite), re.IGNORECASE)]
    if made_exact:
        problems.append(f"made an approximate number exact ({', '.join(made_exact)})")
    on, rn = word_numbers(original), word_numbers(rewrite)
    lost_words = [w for w, v in on.items() if w not in rn and v not in numbers_in(rewrite)]
    if lost_words:
        problems.append(f"dropped numbers from the original ({', '.join(lost_words)})")
    added_words = [w for w, v in rn.items() if w not in on and v not in numbers_in(original)]
    if added_words:
        problems.append(f"added numbers that aren't in the original ({', '.join(added_words)})")
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
    plain_rw = normalize(re.sub(r"\[[^\]]*\]", " ", rewrite)).lower()
    if ok and ok[0] not in nk:
        # "Worked with X to review" → "Reviewed … with X" keeps the collaboration while the partner is still named.
        partner_kept = ok[0] == "collaborate" and len(ok) > 1 and ok[1] in nk and re.search(r"\b(with|alongside)\b", plain_rw)
        if not partner_kept:
            problems.append(f"changed the kind of work (the original says you {_KIND_PHRASE.get(ok[0], ok[0])})")
    if "help" in ok and "help" not in nk:
        problems.append("dropped 'helped', which overstates your part")
    owned = re.search(r"\b(responsible for|in charge of|accountable for|owned|ownership of)\b", normalize(original).lower())
    for k, what in _ESCALATIONS.items():
        if k in nk and k not in ok and not (k == "improve" and _has_result(original)) and not (k == "create" and ok and ok[0] == "create") \
                and not (k == "lead" and owned):
            problems.append(f"turned it into {what} the original doesn't describe")

    orig_lemmas = _lemma_set(words(original))
    leading = sorted({w for ph in placeholders(rewrite) for w in words(ph) if lemma(w) in _OUTCOME_LEMMAS and lemma(w) not in orig_lemmas})
    if leading:
        problems.append(f"has a placeholder that suggests a result you may not have ({', '.join(leading)}); placeholders should only ask for scale or scope")
    new_outcomes = sorted({w for w in words(rewrite, keep_brackets=False) if lemma(w) in _OUTCOME_LEMMAS and lemma(w) not in orig_lemmas})
    if new_outcomes:
        problems.append(f"added an outcome or claim the original doesn't state ({', '.join(new_outcomes)})")

    problems += meaning_problems(original, rewrite)

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
