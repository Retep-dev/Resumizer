"""Stage 3a — rewrite bullets so they read stronger, without adding facts.

For each bullet:
  1. extract its facts in code (numbers, tools, kind of action, whether it states a result);
  2. ask the model for two candidates: "safe" (better wording, same facts) and
     "strong" (most compelling honest version, may add one [placeholder] the
     candidate fills in);
  3. verify every candidate against the original in code (bullet_facts.verify_rewrite);
  4. keep the best candidate that passes and is a real improvement, not a cosmetic edit;
  5. otherwise keep the original wording and ask for the missing detail instead.
One targeted retry is made for bullets whose candidates all failed or were skipped.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from app.agents.safety import UNTRUSTED_DATA_NOTE
from app.agents.bullet_facts import (
    extract_facts, lemma, placeholders, verb_kinds, verification_note, verify_rewrite, words,
)
from app.llm import ChatClient, complete_json
from app.schemas.resume import BulletPointRewrite, ResumeRewriteReport, ResumeSchema, WorkExperienceRewrite
from app.services.text_utils import normalize, numbers_in, term_in_text, unsupported_numbers

REWRITE_SYSTEM_PROMPT = """You are an expert resume editor. You make each bullet read like a strong, specific professional achievement, using only the facts that bullet already contains.

For every bullet you are given its text and its facts (numbers, tools, kind of action, whether it states a result). Write two candidates:
- "safe": clearly better wording with exactly the same facts.
- "strong": the most compelling honest version. It may add ONE bracketed placeholder for a missing NUMBER (scale or frequency), written with letters not digits, e.g. "[N users]", "[N a week]", "[X% of tickets]". Never a placeholder that suggests a result or benefit.

How to improve a bullet (use whatever fits):
1. Open with a precise, strong verb of the SAME kind as the original: maintained → maintained/ran/kept; built → built/developed/designed; helped → helped/supported/contributed to; worked with → partnered/collaborated with; mentored → mentored/coached.
2. If the bullet states a result, lead with it: "Built X, which doubled Y" → "Doubled Y by building X".
3. Cut filler: "Responsible for", "Worked on", "Duties included", "Various", "Successfully".
4. Be concrete with what the bullet already says: what it was, who it was for, how often.
5. Use the posting's wording only for things the bullet already describes (see posting_terms).
6. One sentence, under 30 words, no first person.

Never:
- add numbers, tools, skills, team sizes, purposes, benefits or results the bullet doesn't state (no "improving accuracy", "saving time", "boosting performance", "for stakeholders");
- upgrade the action (helped → led, maintained → built, mentored → managed, worked with → led);
- move facts in from another bullet or merge bullets;
- use any skill from missing_skills, even inside a placeholder.

Examples (other professions):
- "Responsible for training new cashiers." → safe: "Trained new cashiers." strong: "Trained [N] new cashiers."
- "Reduced average patient wait time from 40 to 25 minutes by reorganising triage." → safe: "Cut average patient wait time from 40 to 25 minutes by reorganising triage." strong: "Cut average patient wait time from 40 to 25 minutes by reorganising the triage process [across N clinics]."
- "Helped prepare quarterly board reports." → safe: "Helped prepare the quarterly board reports." strong: "Helped prepare quarterly board reports [covering which areas]."
- Wrong: "Helped prepare quarterly board reports." → "Led quarterly board reporting, improving executive decisions." (upgrades the action and invents a benefit)

Also write "questions": 1-2 short questions whose answers would fill the placeholder or make the bullet stronger.
If a summary is given, return an improved "summary" (2 sentences max, only facts from the resume), or null.

Return one JSON object:
{"bullets": [{"id": int, "safe": str, "strong": str, "questions": [str]}], "summary": str|null}
Include every bullet id you were given."""
REWRITE_SYSTEM_PROMPT += UNTRUSTED_DATA_NOTE

FILLER_RE = re.compile(r"^\s*(?:(?:was|were|i was)\s+)?(?:responsible for|worked on|tasked with|duties included|in charge of|involved in|part of the team that|did)\b", re.IGNORECASE)
NO_CHANGE_NOTE = "No stronger wording was found that keeps your facts exactly. Answer the questions below to strengthen it."
NUMERIC_PLACEHOLDER = re.compile(r"\b[NXY]\b|how (?:many|much|often|long)|%|\bnumber\b", re.IGNORECASE)
PLACEHOLDER_NOTE = "Replace the [bracketed] parts with your real details, or delete them, before using this."


class _Candidate(BaseModel):
    id: int
    safe: Optional[str] = None
    strong: Optional[str] = None
    questions: List[str] = Field(default_factory=list)

    @field_validator("questions", mode="before")
    @classmethod
    def _qs(cls, v):
        return [q for q in (v or []) if isinstance(q, str)]


class _Proposal(BaseModel):
    bullets: List[_Candidate] = Field(default_factory=list)
    summary: Optional[str] = None


def _norm(s: str) -> str:
    return " ".join(normalize(s).lower().split()).strip(" .")


def follow_up_questions(bullet: str) -> List[str]:
    """Deterministic prompts for facts that would strengthen a bullet. They ask; they never assume."""
    qs = []
    if not numbers_in(bullet):
        qs.append("Can you add a number that shows scale or result — how many, how often, how much, or how much faster?")
    qs.append("What changed because of this work, and who relied on it?")
    return qs


def change_ratio(original: str, rewrite: str) -> float:
    """Share of word positions that differ (outside placeholders), 0..1."""
    a = [lemma(w) for w in words(original)]
    b = [lemma(w) for w in words(rewrite, keep_brackets=False)]
    if not a:
        return 1.0
    # Longest common subsequence on words.
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    return round(1 - dp[0][0] / max(len(a), len(b)), 3)


def improvement_score(original: str, rewrite: str, posting_terms: List[str]) -> Tuple[int, List[str]]:
    """How much better a (verified) rewrite is, and why. Code, not opinion, so it can be audited."""
    score, why = 0, []
    if FILLER_RE.search(original) and not FILLER_RE.search(rewrite):
        score += 2
        why.append("cut filler")
    ok, nk = verb_kinds(original), verb_kinds(rewrite)
    if ok and nk and ok[0] != "improve" and nk[0] == "improve":
        score += 2
        why.append("leads with the result")
    gained = [t for t in posting_terms if term_in_text(t, rewrite) and not term_in_text(t, original)]
    if gained:
        score += 1
        why.append("uses the posting's wording")
    if placeholders(rewrite):
        score += 1
        why.append("asks for a missing metric")
    ratio = change_ratio(original, rewrite)
    if ratio >= 0.25:
        score += 1
        why.append("clearer wording")
    plain = re.sub(r"\[[^\]]*\]", "", rewrite)
    if len(plain.split()) > 1.6 * len(original.split()) + 3:
        score -= 1
        why.append("longer")
    if ratio < 0.12 and not placeholders(rewrite):
        score = min(score, 0)  # cosmetic: an article or a comma isn't an improvement
    return score, why


def _known_skills(resume: ResumeSchema, supported: List[str]) -> List[str]:
    return list(dict.fromkeys(resume.technical_skills + resume.tools_and_frameworks + supported))


def _items(resume: ResumeSchema, known: List[str]) -> List[Dict]:
    out, i = [], 1
    for ji, job in enumerate(resume.work_experience):
        for b in job.bullet_points:
            if b.strip():
                f = extract_facts(b, known)
                out.append({"id": i, "job": ji, "role": " at ".join(x for x in (job.job_title, job.company) if x), "text": b, "facts": f})
                i += 1
    return out


def judge(item: Dict, cand: Optional[_Candidate], *, missing: List[str], known: List[str], all_bullets: List[str],
          posting_terms: List[str]) -> Tuple[Optional[BulletPointRewrite], List[str]]:
    """Pick the best verified candidate. Returns (rewrite or None, problems with the rejected candidates)."""
    original = item["text"]
    others = [b for b in all_bullets if b != original]
    passed: Dict[str, Tuple[str, int, List[str]]] = {}
    problems = []
    for kind in ("safe", "strong"):
        text = (getattr(cand, kind) or "").strip() if cand else ""
        if not text or _norm(text) == _norm(original):
            continue
        p = verify_rewrite(original, text, missing=missing, known_skills=known, other_bullets=others)
        if len(placeholders(text)) > 1:
            p.append("left more than one blank to fill in")
        vague = [ph for ph in placeholders(text) if not NUMERIC_PLACEHOLDER.search(ph)]
        if vague:
            p.append(f"has a placeholder that doesn't ask for a number ([{vague[0]}])")
        if p:
            problems.append(f"{kind}: " + "; ".join(p))
            continue
        score, why = improvement_score(original, text, posting_terms)
        if score > 0:
            passed[kind] = (text, score, why)
    # A clean wording improvement wins; the missing metric is then asked for as a question instead of a [blank].
    pick = passed.get("safe") if "safe" in passed and not placeholders(passed["safe"][0]) else None
    if not pick and passed:
        pick = max(passed.values(), key=lambda v: v[1])
    best = None
    if pick:
        text, score, why = pick
        qs = [q.strip() for q in (cand.questions if cand else []) if q.strip()][:2] or follow_up_questions(original)
        best = BulletPointRewrite(
            original_bullet=original, rewritten_bullet=text, status="rewritten", star_action="", star_result="",
            added_keywords=[t for t in posting_terms if term_in_text(t, text) and term_in_text(t, original)],
            needs_confirmation=qs, note=PLACEHOLDER_NOTE if placeholders(text) else None,
            checks=verification_note(item["facts"]) + ([", ".join(why)] if why else []),
        )
    return best, problems


def _kept(item: Dict, cand: Optional[_Candidate], problems: List[str]) -> BulletPointRewrite:
    original = item["text"]
    note = ("Rewrite withheld: " + problems[0].split(": ", 1)[1] + ".") if problems else NO_CHANGE_NOTE
    qs = [q.strip() for q in (cand.questions if cand else []) if q.strip()][:2] or follow_up_questions(original)
    return BulletPointRewrite(original_bullet=original, rewritten_bullet=original, status="kept_original", note=note, needs_confirmation=qs)


def _check_summary(summary: Optional[str], resume: ResumeSchema, resume_text: str, missing: List[str]) -> Tuple[Optional[str], List[str]]:
    from app.agents.bullet_facts import OUTCOME_WORDS
    s = (summary or "").strip()
    if not s:
        return None, []
    if resume.summary and _norm(s) == _norm(resume.summary):
        return None, ["The AI didn't suggest a different summary, so your original is unchanged."]
    why = []
    bad = unsupported_numbers(s, resume_text)
    if bad:
        why.append("numbers not in your resume (" + ", ".join(sorted(bad)) + ")")
    claimed = [k for k in missing if term_in_text(k, s) and not term_in_text(k, resume_text)]
    if claimed:
        why.append("skills your resume doesn't show (" + ", ".join(claimed) + ")")
    resume_lemmas = {lemma(w) for w in words(resume_text)}
    outcomes = sorted({w for w in words(s) if lemma(w) in {lemma(o) for o in OUTCOME_WORDS} and lemma(w) not in resume_lemmas})
    if outcomes:
        why.append("claims your resume doesn't make (" + ", ".join(outcomes) + ")")
    if re.search(r"\b\d+\+?\s*years?\b", s, re.I) and not re.search(r"\b\d+\+?\s*years?\b", resume_text, re.I):
        why.append("a years-of-experience figure your resume doesn't state")
    if why:
        return None, ["The suggested summary was withheld because it included " + " and ".join(why) + "."]
    return s, []


SINGLE_SYSTEM_PROMPT = REWRITE_SYSTEM_PROMPT.split("Also write \"questions\"")[0] + """Answer for ONE bullet, in exactly this plain-text format and nothing else:
SAFE: <rewrite>
STRONG: <rewrite>
QUESTION: <one question>""" + UNTRUSTED_DATA_NOTE


def _parse_single(text: str, bullet_id: int) -> _Candidate:
    def grab(label: str) -> Optional[str]:
        m = re.search(rf"^\s*\**{label}\**\s*:\s*(.+)$", text or "", re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip().strip('"').strip() if m else None
    q = grab("QUESTION")
    return _Candidate(id=bullet_id, safe=grab("SAFE"), strong=grab("STRONG"), questions=[q] if q else [])


async def _propose_single(client: ChatClient, items: List[Dict], supported: List[str], missing: List[str], job_description: str):
    """One call per bullet, plain-text answer: some models copy their input when given a batch as JSON."""
    import asyncio
    sem = asyncio.Semaphore(4)
    model = {"m": ""}

    async def one(it):
        user = (f"Role: {it['role']}\nBullet: {it['text']}\nFacts: {json.dumps(it['facts'].summary())}\n"
                f"posting_terms: {', '.join(supported) or '(none)'}\nmissing_skills: {', '.join(missing) or '(none)'}\n"
                f"Job posting (for wording only): {job_description[:1500]}")
        async with sem:
            out = await client.complete([{"role": "system", "content": SINGLE_SYSTEM_PROMPT}, {"role": "user", "content": user}],
                                        temperature=0.3, max_tokens=1500)
        model["m"] = out.model
        return _parse_single(out.text, it["id"])

    cands = await asyncio.gather(*(one(it) for it in items), return_exceptions=True)
    errors = [c for c in cands if isinstance(c, Exception)]
    if errors and len(errors) == len(cands):
        raise errors[0]
    return _Proposal(bullets=[c for c in cands if isinstance(c, _Candidate)], summary=None), model["m"]


async def rewrite_with_ai(client: ChatClient, resume: ResumeSchema, resume_text: str, job_description: str,
                          supported: List[str], missing: List[str], mode: Optional[str] = None) -> Tuple[ResumeRewriteReport, List[str], str]:
    known = _known_skills(resume, supported)
    items = _items(resume, known)
    if not items:
        return ResumeRewriteReport(), ["No bullet points were found under your roles, so there was nothing to rewrite."], ""
    all_bullets = [it["text"] for it in items]

    def payload(subset: List[Dict]) -> Dict:
        return {
            "posting_terms": supported,
            "missing_skills": missing,
            "summary": resume.summary or None,
            "bullets": [{"id": it["id"], "role": it["role"], "text": it["text"], "facts": it["facts"].summary()} for it in subset],
        }

    mode = mode or os.getenv("REWRITE_MODE", "batch")
    if mode == "single":
        proposal, model = await _propose_single(client, items, supported, missing, job_description)
    else:
        user = f"Resume bullets (JSON):\n{json.dumps(payload(items), ensure_ascii=False)}\n\nJob posting (for wording only):\n{job_description[:5000]}"
        proposal, model = await complete_json(client, REWRITE_SYSTEM_PROMPT, user, _Proposal, temperature=0.3, max_tokens=6000)
    cands = {c.id: c for c in proposal.bullets}

    results: Dict[int, BulletPointRewrite] = {}
    problems: Dict[int, List[str]] = {}
    for it in items:
        best, p = judge(it, cands.get(it["id"]), missing=missing, known=known, all_bullets=all_bullets, posting_terms=supported)
        if best:
            results[it["id"]] = best
        else:
            problems[it["id"]] = p

    # One targeted retry: skipped bullets, and bullets whose candidates broke the rules.
    retry = [it for it in items if it["id"] not in results and (it["id"] not in cands or problems.get(it["id"]))]
    if retry:
        notes = "\n".join(
            f"- Bullet {it['id']}: " + ("you skipped it." if it["id"] not in cands else "your versions were rejected because they " + " | ".join(problems[it["id"]]) + ".")
            for it in retry)
        retry_user = (f"Resume bullets (JSON):\n{json.dumps(payload(retry), ensure_ascii=False)}\n\nJob posting (for wording only):\n{job_description[:5000]}"
                      f"\n\nRewrite these bullets again, following the rules strictly:\n{notes}")
        try:
            again, _ = await complete_json(client, REWRITE_SYSTEM_PROMPT, retry_user, _Proposal, temperature=0.2, max_tokens=4000)
            for c in again.bullets:
                it = next((x for x in retry if x["id"] == c.id), None)
                if not it:
                    continue
                best, p = judge(it, c, missing=missing, known=known, all_bullets=all_bullets, posting_terms=supported)
                if best:
                    results[it["id"]] = best
                    problems.pop(it["id"], None)
                elif p:
                    problems[it["id"]] = p
                cands.setdefault(c.id, c)
        except Exception:
            pass  # keep what we have

    exps: List[WorkExperienceRewrite] = []
    for ji, job in enumerate(resume.work_experience):
        bullets = [results.get(it["id"]) or _kept(it, cands.get(it["id"]), problems.get(it["id"], [])) for it in items if it["job"] == ji]
        if bullets:
            exps.append(WorkExperienceRewrite(company=job.company, job_title=job.job_title, rewritten_bullets=bullets))

    summary, warnings = _check_summary(proposal.summary, resume, resume_text, missing)
    withheld = sum(1 for e in exps for b in e.rewritten_bullets if (b.note or "").startswith("Rewrite withheld"))
    kept = sum(1 for e in exps for b in e.rewritten_bullets if b.note == NO_CHANGE_NOTE)
    if withheld:
        warnings.append(f"{withheld} suggested rewrite(s) were withheld because they changed your facts; the original wording is shown instead.")
    if kept:
        warnings.append(f"No safe improvement was found for {kept} bullet(s); they're shown with questions instead.")
    return ResumeRewriteReport(tailored_summary=summary, rewritten_experiences=exps), warnings, model


# ── Compatibility for callers/tests that check one rewrite at a time ──

def check_bullet(rw: BulletPointRewrite, original: str, missing: List[str], supported: List[str],
                 known_skills: Optional[List[str]] = None, other_bullets: Optional[List[str]] = None) -> List[str]:
    """Reasons a rewrite isn't trustworthy (empty list = fine)."""
    return verify_rewrite(original, rw.rewritten_bullet, missing=missing, known_skills=known_skills or [], other_bullets=other_bullets or [])
