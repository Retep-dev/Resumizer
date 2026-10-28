"""What the coach may say about the candidate, worked out in code before the model answers.

Four kinds of evidence:
  documented    — posting requirements the resume shows, with the line that shows it
  related       — transferable experience for a missing requirement (NOT the skill itself)
  said_in_chat  — what the candidate told the coach: used / course or project / learning / not used
  no_evidence   — missing requirements with nothing to point to
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.services.text_utils import normalize, term_in_text

# missing-requirement pattern → [(resume pattern, how it relates)]. Deliberately conservative:
# each relation is described as related experience, never as the skill itself.
RELATED: List[Tuple[str, List[Tuple[str, str]]]] = [
    (r"\baws\b|azure|\bgcp\b|google cloud|\bcloud\b", [(r"snowflake|bigquery|redshift|databricks", "cloud data-warehouse work, not hands-on with this cloud platform")]),
    (r"kafka|streaming", [(r"airflow|pipeline|etl", "batch data pipelines, not streaming")]),
    (r"terraform|infrastructure as code", [(r"\bgit\b|\bdbt\b|ci/cd", "managing work as version-controlled code, not infrastructure")]),
    (r"typescript", [(r"javascript", "JavaScript, which TypeScript builds on")]),
    (r"graphql", [(r"\brest\b|\bapis?\b", "working with APIs, not GraphQL specifically")]),
    (r"next\.js", [(r"\breact\b", "React, which Next.js is built on")]),
    (r"ci/cd", [(r"pull request|unit test|jest|\bgit\b", "testing and code-review workflow, not owning CI/CD")]),
    (r"leadership|\blead\b|team of|manage(?:ment)? of", [(r"supervis|mentor|coach|train|onboard|orient", "supervising, mentoring or training people")]),
    (r"stakeholder|communication", [(r"report\w* .{0,40}\bto\b|present|partner|worked with|department heads|coordinat|liais", "working with or reporting to other teams")]),
    (r"budget", [(r"\$\s?\d|\bbudget\b", "budget responsibility")]),
    (r"financial model|forecast", [(r"variance|budget|excel", "spreadsheet analysis of actuals against budget")]),
    (r"power bi|looker|dashboard", [(r"tableau|dashboard|\breport\b", "building reports or dashboards in other tools")]),
    (r"hubspot|salesforce|\bcrm\b|marketing automation", [(r"mailchimp|email campaign", "email-marketing platforms")]),
    (r"a/b test|experiment", [(r"campaign", "running campaigns, not structured A/B tests")]),
    (r"linkedin", [(r"meta ads|instagram|facebook|paid social", "paid social on other platforms")]),
    (r"curriculum|education program|training program", [(r"orient|train|education session|teach", "training and orienting staff")]),
    (r"simulation", [(r"train|education session|orient", "hands-on staff training, not simulation")]),
    (r"competency assess", [(r"train|orient|mentor", "training staff, not formal assessment")]),
    (r"adult learning|presentation", [(r"education session|train|teach|present", "running teaching sessions")]),
    (r"\blean\b|six sigma|continuous improvement|process improvement", [(r"\bcut\b|reduc|introduc|checklist|automat", "process changes with measured results, not formal Lean/Six Sigma")]),
    (r"\bkpi", [(r"\d+(?:\.\d+)?\s*%|per month|per shift|from \d", "tracking measurable results")]),
    (r"\bsap\b|\berp\b", [(r"\bwms\b|manhattan|netsuite|\berp\b", "other operations or finance systems")]),
    (r"\bsql\b", [(r"excel|tableau|power bi", "analysing data in other tools, not SQL")]),
]

_SKILL_SENTENCE = r"[^.?!\n]*"


@dataclass
class Ledger:
    documented: List[Tuple[str, str]] = field(default_factory=list)       # (skill, resume line)
    related: List[Tuple[str, str, str]] = field(default_factory=list)     # (missing skill, resume line, relation)
    said_in_chat: Dict[str, str] = field(default_factory=dict)            # skill → used | course_or_project | learning | not_used
    no_evidence: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    def may_claim(self) -> set:
        return {s for s, k in self.said_in_chat.items() if k == "used"}

    def as_prompt(self) -> str:
        lines = ["Documented on the resume (can be stated as experience):"]
        lines += [f"- {s}: \"{ev}\"" for s, ev in self.documented] or ["- (none of the posting's requirements)"]
        lines.append("Related experience for missing requirements (describe it as related, NEVER as the missing skill itself):")
        lines += [f"- {s}: not on the resume. Related: \"{ev}\" ({why})" for s, ev, why in self.related] or ["- (none found)"]
        if self.said_in_chat:
            labels = {"used": "says they have used it (not on the resume yet; suggest adding it only as they described it)",
                      "course_or_project": "took a course or did a project (not work experience; can go under courses or projects)",
                      "learning": "is learning it (not experience)", "not_used": "says they have NOT used it"}
            lines.append("What the candidate told you in this chat:")
            lines += [f"- {s}: {labels[k]}" for s, k in self.said_in_chat.items()]
        lines.append("Missing with no evidence (never imply the candidate has these):")
        lines.append("- " + (", ".join(self.no_evidence) if self.no_evidence else "(none)"))
        return "\n".join(lines)


def _lines(text: str) -> List[str]:
    out = []
    for raw in normalize(text or "").splitlines():
        line = raw.strip(" •●▪*-\t")
        if len(line) > 3:
            out.append(line)
    return out


def related_evidence(skill: str, resume_text: str) -> Optional[Tuple[str, str]]:
    s = skill.lower()
    for pattern, links in RELATED:
        if not re.search(pattern, s):
            continue
        for resume_pattern, why in links:
            for line in _lines(resume_text):
                if re.search(resume_pattern, line, re.IGNORECASE):
                    return line, why
    return None


def said_in_chat(messages: List[str], skills: List[str]) -> Dict[str, str]:
    """What the candidate said about each skill, latest statement wins. Deterministic phrase matching."""
    out: Dict[str, str] = {}
    for msg in messages:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", normalize(msg)):
            low = sentence.lower().strip()
            # A question ("Do I have Kafka experience?") is not a statement about the candidate.
            if low.endswith("?") or re.match(r"^(?:so\s+|and\s+|but\s+)?(do|does|did|have|has|am|is|are|was|were|can|could|should|would|will|may|how|what|which|where|when|why|who)\b", low):
                continue
            for skill in skills:
                if not term_in_text(skill, sentence):
                    continue
                if re.search(r"\b(haven'?t|have not|never|don'?t|do not|didn'?t|did not|no)\b", low):
                    out[skill] = "not_used"
                elif re.search(r"\b(course|tutorial|certificat\w*|bootcamp|side project|personal project|workshop|class)\b", low):
                    out[skill] = "course_or_project"
                elif re.search(r"\b(learning|studying|want to learn|plan to learn|picking up)\b", low):
                    out[skill] = "learning"
                elif re.search(r"\b(i|i've|i have|i'd|we)\b.{0,30}\b(used|use|worked with|work with|built|deployed|ran|run|set up|managed|experience)\b", low):
                    out[skill] = "used"
    return out


def build_ledger(resume_text: str, analysis: dict, user_messages: List[str]) -> Ledger:
    ats = (analysis or {}).get("ats_score") or {}
    evidence = {e.get("keyword"): e.get("evidence") for e in ats.get("keyword_evidence") or [] if e.get("found")}
    matched = list(ats.get("matched_keywords") or [])
    missing = list(ats.get("missing_keywords") or [])
    led = Ledger(missing=missing)
    led.documented = [(m, evidence.get(m) or "listed on the resume") for m in matched]
    led.said_in_chat = said_in_chat(user_messages, missing + matched)
    for m in missing:
        rel = related_evidence(m, resume_text)
        if rel:
            led.related.append((m, rel[0], rel[1]))
        if m not in led.said_in_chat or led.said_in_chat[m] == "not_used":
            if not rel:
                led.no_evidence.append(m)
    return led
