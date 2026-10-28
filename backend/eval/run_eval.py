"""Reproducible writing evaluation: rewrites (before/after pipeline) and coach grounding.

    python -m eval.run_eval --request eval/request.json --out eval_out

Inputs are fixed: resumes are parsed by rules (not by the model under test) and
each case has a fixed requirement list, so every model rewrites the same bullets
against the same "supported" and "missing" skills. Every raw output is saved for
human review alongside the automated audit.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.bullet_facts import new_content_words, placeholders, verify_rewrite  # noqa: E402
from app.agents.career_coach_agent import (  # noqa: E402
    borrowed_from_posting, claimed_missing, coach_reply, merged_bullets, resume_bullets, target_bullets,
)
from app.agents.resume_parser_agent import rule_based_parse  # noqa: E402
from app.agents.resume_rewrite_agent import change_ratio, improvement_score  # noqa: E402
from app.agents.resume_rewrite_agent import rewrite_with_ai as rewrite_v2  # noqa: E402
from app.agents.scoring import score_resume  # noqa: E402
from app.llm import ChatClient, Completion  # noqa: E402
from app.llm.router import client_from_spec  # noqa: E402
from app.schemas.resume import JobRequirement, JobRequirements  # noqa: E402
from app.services.text_utils import term_in_text, unsupported_numbers  # noqa: E402
from eval.baseline_coach import chat_with_career_coach as coach_baseline  # noqa: E402
from eval.baseline_rewrite import rewrite_with_ai as rewrite_baseline  # noqa: E402
from eval.cases import CASES  # noqa: E402

PIPELINES = {"baseline": rewrite_baseline, "v2": rewrite_v2,
             "v2single": lambda *a: rewrite_v2(*a, mode="single")}
TIMEOUT = {"s": 120.0}
COACH = {"impl": "v2"}


def make_client(spec: str) -> ChatClient:
    return client_from_spec(spec, timeout=TIMEOUT["s"])


@dataclass
class Recorder(ChatClient):
    inner: ChatClient
    calls: List[Dict] = field(default_factory=list)

    async def complete(self, messages, **kw) -> Completion:
        t0 = time.monotonic()
        try:
            out = await self.inner.complete(messages, **kw)
        except Exception as e:
            self.calls.append({"ok": False, "seconds": round(time.monotonic() - t0, 2), "error": f"{type(e).__name__}: {getattr(e, 'message', e)}"[:300]})
            raise
        self.calls.append({"ok": True, "model": out.model, "provider": out.provider, "seconds": round(time.monotonic() - t0, 2),
                           "prompt_tokens": out.prompt_tokens, "completion_tokens": out.completion_tokens})
        return out

    def take(self) -> List[Dict]:
        c, self.calls = self.calls, []
        return c


def context(case: Dict) -> Dict:
    resume, _ = rule_based_parse(case["resume"])
    supported = [t for t in case["requirements"] if term_in_text(t, case["resume"])]
    missing = [t for t in case["requirements"] if t not in supported]
    reqs = JobRequirements(title=None, requirements=[JobRequirement(term=t) for t in case["requirements"]])
    ats, gap = score_resume(resume, case["resume"], reqs, "ai")
    known = list(dict.fromkeys(resume.technical_skills + resume.tools_and_frameworks + supported))
    analysis = {"status": "complete", "resume_data": resume.model_dump(), "ats_score": ats.model_dump(), "skill_gap": gap.model_dump()}
    return {"resume": resume, "supported": supported, "missing": missing, "known": known, "analysis": analysis,
            "bullets": [b for j in resume.work_experience for b in j.bullet_points]}


def audit_bullet(b, ctx) -> Dict:
    original, text = b.original_bullet, b.rewritten_bullet
    changed = b.status == "rewritten" and text.strip() != original.strip()
    problems = verify_rewrite(original, text, missing=ctx["missing"], known_skills=ctx["known"], other_bullets=ctx["bullets"]) if changed else []
    score, why = improvement_score(original, text, ctx["supported"]) if changed else (0, [])
    return {
        "original": original, "output": text, "status": b.status, "note": b.note, "questions": b.needs_confirmation,
        "changed": changed, "audit_problems": problems, "improvement_score": score, "improvement": why,
        "change_ratio": change_ratio(original, text) if changed else 0.0, "placeholders": placeholders(text),
        "new_words": new_content_words(original, text) if changed else [],
        "numbers_kept": not [n for n in re.findall(r"\d+(?:[.,]\d+)?", original) if n not in text],
    }


async def eval_rewrite(spec: str, pipeline: str, case: Dict, ctx: Dict) -> Dict:
    rec = Recorder(make_client(spec))
    t0 = time.monotonic()
    try:
        report, warnings, model = await PIPELINES[pipeline](rec, ctx["resume"], case["resume"], case["jd"], ctx["supported"], ctx["missing"])
    except Exception as e:
        return {"case": case["id"], "error": f"{type(e).__name__}: {getattr(e, 'message', e)}"[:400], "calls": rec.take(),
                "seconds": round(time.monotonic() - t0, 1)}
    bullets = [audit_bullet(b, ctx) for e in report.rewritten_experiences for b in e.rewritten_bullets]
    return {"case": case["id"], "seconds": round(time.monotonic() - t0, 1), "calls": rec.take(), "warnings": warnings,
            "summary_out": report.tailored_summary, "bullets": bullets, "covered": len(bullets), "total": len(ctx["bullets"])}


def audit_coach_turn(question: str, reply: str, case: Dict, ctx: Dict) -> Dict:
    a: Dict = {}
    a["claims_missing_skill"] = claimed_missing(reply, ctx["missing"], case["resume"])
    targets = target_bullets(question, resume_bullets(case["resume"], ctx["analysis"]))
    if targets:
        a["rewrite_target"] = targets
        a["merged"] = merged_bullets(reply, targets, ctx["bullets"], question)
        a["borrowed"] = borrowed_from_posting(reply, targets, case["resume"], case["jd"])
    if re.search(r"yes or no first", question, re.I):
        a["answered_no_first"] = bool(re.match(r"\W*no\b", reply.strip(), re.I))
    bad = unsupported_numbers(re.sub(r"\[[^\]]*\]", "", reply), case["resume"] + "\n" + case["jd"])
    a["numbers_not_in_resume_or_posting"] = sorted(bad)
    a["guard_note_shown"] = bool(re.search(r"\n\nNote: ", reply))
    return a


async def eval_coach(spec: str, case: Dict, ctx: Dict) -> Dict:
    rec = Recorder(make_client(spec))
    history, turns = [], []
    for q in case["coach"]:
        t0 = time.monotonic()
        try:
            if COACH["impl"] == "v2":
                res = await coach_reply(q, history, case["resume"], case["jd"], ctx["analysis"], client=rec)
                reply, check, notes = res.reply, res.status, res.notes
            else:
                reply, check, notes = await coach_baseline(q, history, case["resume"], case["jd"], ctx["analysis"], client=rec), None, []
        except Exception as e:
            turns.append({"question": q, "error": f"{type(e).__name__}: {getattr(e, 'message', e)}"[:300], "calls": rec.take()})
            continue
        turns.append({"question": q, "reply": reply, "check": check, "check_notes": notes, "seconds": round(time.monotonic() - t0, 1), "calls": rec.take(),
                      "audit": audit_coach_turn(q, reply, case, ctx)})
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": reply}]
    return {"case": case["id"], "turns": turns}


def summarize_rewrites(runs: List[Dict]) -> Dict:
    bullets = [b for r in runs for b in r.get("bullets", [])]
    calls = [c for r in runs for c in r.get("calls", [])]
    total = sum(r.get("total", 0) for r in runs)
    accepted = [b for b in bullets if b["changed"]]
    return {
        "cases": len(runs), "errors": sum(1 for r in runs if "error" in r), "bullets": total, "covered": len(bullets),
        "rewritten": len(accepted),
        "rewritten_and_audit_clean": sum(1 for b in accepted if not b["audit_problems"]),
        "audit_failures_accepted": sum(1 for b in accepted if b["audit_problems"]),
        "meaningful (score>=1, clean)": sum(1 for b in accepted if not b["audit_problems"] and b["improvement_score"] >= 1),
        "with_placeholder": sum(1 for b in accepted if b["placeholders"]),
        "avg_change_ratio": round(sum(b["change_ratio"] for b in accepted) / len(accepted), 3) if accepted else 0,
        "seconds_per_resume": round(sum(r.get("seconds", 0) for r in runs) / max(len(runs), 1), 1),
        "calls": len(calls), "failed_calls": sum(1 for c in calls if not c["ok"]),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in calls),
    }


def summarize_coach(runs: List[Dict]) -> Dict:
    turns = [t for r in runs for t in r["turns"]]
    ok = [t for t in turns if "reply" in t]
    yn = [t for t in ok if "answered_no_first" in t["audit"]]
    rw = [t for t in ok if "rewrite_target" in t["audit"]]
    calls = [c for t in turns for c in t.get("calls", [])]
    return {
        "turns": len(turns), "errors": len(turns) - len(ok),
        "yes_no_correct": f"{sum(1 for t in yn if t['audit']['answered_no_first'])}/{len(yn)}",
        "replies_claiming_missing_skill": sum(1 for t in ok if t["audit"]["claims_missing_skill"]),
        "rewrites_merging_bullets": sum(1 for t in rw if t["audit"].get("merged")),
        "rewrites_borrowing_posting_terms": sum(1 for t in rw if t["audit"].get("borrowed")),
        "replies_with_unsupported_numbers": sum(1 for t in ok if t["audit"]["numbers_not_in_resume_or_posting"]),
        "guard_notes_shown": sum(1 for t in ok if t["audit"]["guard_note_shown"]),
        "checks": {k: sum(1 for t in ok if t.get("check") == k) for k in ("verified", "corrected", "uncertain")},
        "seconds_per_turn": round(sum(t.get("seconds", 0) for t in ok) / max(len(ok), 1), 1),
        "calls": len(calls), "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in calls),
    }


async def main(req: Dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = [c for c in CASES if req.get("cases", "all") == "all" or c["id"] in req["cases"]]
    ctxs = {c["id"]: context(c) for c in cases}
    results = {"request": req, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "models": {}}
    for spec in req["models"]:
        entry = results["models"].setdefault(spec, {})
        for pipeline in req.get("pipelines", ["v2"]) if "rewrite" in req.get("tasks", ["rewrite"]) else []:
            runs = []
            for c in cases:
                print(f"[{spec}] rewrite/{pipeline}/{c['id']}", flush=True)
                runs.append(await eval_rewrite(spec, pipeline, c, ctxs[c["id"]]))
            entry[f"rewrite_{pipeline}"] = {"summary": summarize_rewrites(runs), "runs": runs}
            print(json.dumps(entry[f"rewrite_{pipeline}"]["summary"]), flush=True)
        for impl in req.get("coach", ["v2"]) if "coach" in req.get("tasks", []) else []:
            COACH["impl"] = impl
            runs = []
            for c in cases:
                print(f"[{spec}] coach-{impl}/{c['id']}", flush=True)
                runs.append(await eval_coach(spec, c, ctxs[c["id"]]))
            entry[f"coach_{impl}"] = {"summary": summarize_coach(runs), "runs": runs}
            print(json.dumps(entry[f"coach_{impl}"]["summary"]), flush=True)
        (out_dir / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", default="eval/request.json")
    ap.add_argument("--out", default="eval_out")
    a = ap.parse_args()
    req = json.loads(Path(a.request).read_text())
    TIMEOUT["s"] = float(req.get("timeout", 120))
    try:
        asyncio.run(main(req, Path(a.out)))
    except Exception:
        traceback.print_exc()
        sys.exit(1)
