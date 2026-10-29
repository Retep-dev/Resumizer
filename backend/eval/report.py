"""Turn eval results.json files into comparison tables and review examples (offline, no network).

    python -m eval.report RESULTS.json [MORE.json ...] > report.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

# Resumizer uses free providers only, so there is no price list; the report shows requests and tokens instead.
PRICES = {"Free providers only (NVIDIA trial, Groq free, Cerebras free)": (0.0, 0.0)}


def wording_improved(b: Dict) -> bool:
    why = b.get("improvement") or []
    return b["changed"] and not b["audit_problems"] and (b["change_ratio"] >= 0.25 or "cut filler" in why or "leads with the result" in why)


def rewrite_row(spec: str, pipe: str, block: Dict) -> Dict:
    runs = block["runs"]
    bullets = [b for r in runs for b in r.get("bullets", [])]
    calls = [c for r in runs for c in r.get("calls", [])]
    total = sum(r.get("total", 0) for r in runs)
    changed = [b for b in bullets if b["changed"]]
    clean = [b for b in changed if not b["audit_problems"]]
    ok_runs = [r for r in runs if "error" not in r]
    return {
        "model": spec, "pipeline": pipe, "resumes": f"{len(ok_runs)}/{len(runs)}", "bullets": total,
        "accepted": len(changed), "accepted_unsafe": len(changed) - len(clean),
        "wording_improved": sum(1 for b in clean if wording_improved(b)),
        "placeholder_only": sum(1 for b in clean if not wording_improved(b) and b["placeholders"]),
        "kept_original": total - len(changed),
        "s_per_resume": round(sum(r.get("seconds", 0) for r in ok_runs) / max(len(ok_runs), 1), 1),
        "in_tok_per_resume": round(sum(c.get("prompt_tokens", 0) for c in calls) / max(len(runs), 1)),
        "out_tok_per_resume": round(sum(c.get("completion_tokens", 0) for c in calls) / max(len(runs), 1)),
        "failed_calls": sum(1 for c in calls if not c["ok"]),
    }


def coach_row(spec: str, impl: str, block: Dict) -> Dict:
    s = block["summary"]
    turns = [t for r in block["runs"] for t in r["turns"] if "reply" in t]
    calls = [c for r in block["runs"] for t in r["turns"] for c in t.get("calls", [])]
    return {
        "model": spec, "coach": impl, "turns": s["turns"], "errors": s["errors"], "yes/no correct": s["yes_no_correct"],
        "claims missing skill": s["replies_claiming_missing_skill"], "rewrite merges": s["rewrites_merging_bullets"],
        "rewrite borrows posting": s["rewrites_borrowing_posting_terms"],
        "checks": s.get("checks", {}), "s_per_turn": s["seconds_per_turn"],
        "in_tok_per_turn": round(sum(c.get("prompt_tokens", 0) for c in calls) / max(len(turns), 1)),
        "out_tok_per_turn": round(sum(c.get("completion_tokens", 0) for c in calls) / max(len(turns), 1)),
    }


def table(rows: List[Dict]) -> str:
    if not rows:
        return "(none)\n"
    keys = list(rows[0].keys())
    out = "| " + " | ".join(keys) + " |\n|" + "---|" * len(keys) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(r[k]) for k in keys) + " |\n"
    return out


def cost_rows(rewrite_rows: List[Dict], coach_rows: List[Dict]) -> List[Dict]:
    """Cost if a paid model used the same number of tokens as the measured configuration (±~20% by tokenizer)."""
    out = []
    ref_r = max(rewrite_rows, key=lambda r: r["in_tok_per_resume"] + r["out_tok_per_resume"], default=None)
    ref_c = max(coach_rows, key=lambda r: r["in_tok_per_turn"] + r["out_tok_per_turn"], default=None)
    for name, (pin, pout) in PRICES.items():
        rw = (ref_r["in_tok_per_resume"] * pin + ref_r["out_tok_per_resume"] * pout) / 1e6 if ref_r else 0
        ct = (ref_c["in_tok_per_turn"] * pin + ref_c["out_tok_per_turn"] * pout) / 1e6 if ref_c else 0
        out.append({"price list": name, "USD in/out per 1M": f"{pin:.2f} / {pout:.2f}",
                    "rewrite stage per resume": f"${rw:.5f}", "coach turn": f"${ct:.5f}",
                    "per 1,000 analyses + 5 coach turns each": f"${(rw + 5 * ct) * 1000:.2f}"})
    return out


def examples(results: List[Dict], spec: str, pipe: str, limit: int = 40) -> str:
    out = ""
    for res in results:
        block = res["models"].get(spec, {}).get(f"rewrite_{pipe}")
        if not block:
            continue
        for r in block["runs"]:
            for b in r.get("bullets", [])[:limit]:
                tag = "UNSAFE" if b["audit_problems"] else "improved" if wording_improved(b) else "placeholder" if b["changed"] else "kept"
                out += f"- **[{r['case']}] {tag}** — {b['original']}\n"
                if b["changed"]:
                    out += f"  → {b['output']}\n"
                    if b["audit_problems"]:
                        out += f"  ⚠ {'; '.join(b['audit_problems'])}\n"
                elif b.get("note"):
                    out += f"  ({b['note'][:140]})\n"
    return out


def main(paths: List[str]):
    results = [json.loads(Path(p).read_text()) for p in paths]
    rrows, crows, irows, jrows = [], [], [], []
    for res in results:
        for spec, entry in res["models"].items():
            for k, block in entry.items():
                if k.startswith("rewrite_"):
                    rrows.append(rewrite_row(spec, k[8:], block))
                elif k.startswith("coach"):
                    crows.append(coach_row(spec, k.split("_", 1)[1] if "_" in k else "baseline", block))
                elif k == "interview":
                    irows.append({"model": spec, **{x: y for x, y in block["summary"].items() if x not in ("prompt_tokens", "completion_tokens")},
                                  "tokens_per_case": round((block["summary"]["prompt_tokens"] + block["summary"]["completion_tokens"]) / max(block["summary"]["cases"], 1))})
                elif k == "journey":
                    sm = block["summary"]
                    jrows.append({"model": spec, "cases": sm["cases"], "errors": sm["errors"], "stages_fell_back": sm["fell_back"],
                                  **{f"{t}_req/tok": f"{v['requests']} / {v['prompt_tokens'] + v['completion_tokens']:,}" for t, v in sm["per_journey_avg"].items()},
                                  "tokens_per_journey": f"{sm['tokens_per_journey']:,}", "largest_request": sm["max_single_request_tokens"],
                                  "failed_requests": sm["failed_requests"], "analysis_s": sm["analysis_seconds"]})
    print("## Rewrites\n")
    print(table(rrows))
    print("## Coach\n")
    print(table(crows))
    print("## Interview prep\n")
    print(table(irows))
    print("## User journey (1 analysis + 5 coach messages)\n")
    print(table(jrows))
    for spec in {r["model"] for r in rrows}:
        for pipe in ("baseline", "v2"):
            ex = examples(results, spec, pipe)
            if ex:
                print(f"\n## Examples: {spec} / {pipe}\n\n{ex}")


if __name__ == "__main__":
    main(sys.argv[1:])
