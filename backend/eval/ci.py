"""CI entry point: optional model discovery, then the evaluation described in eval/request.json."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval import discover, run_eval  # noqa: E402


def notice(title: str, text: str):
    print(f"::notice title={title}::{' '.join(str(text).split())[:3800]}")


async def main():
    req = json.loads(Path("eval/request.json").read_text())
    out = Path("eval_out")
    out.mkdir(exist_ok=True)
    run_eval.TIMEOUT["s"] = float(req.get("timeout", 120))
    notice("providers", "free only: nvidia, groq, cerebras (no paid provider exists in the code)")
    if req.get("discover"):
        await discover.main(out, timeout=float(req.get("discover_timeout", 60)), limit=int(req.get("discover_limit", 60)),
                            providers=tuple(req.get("discover_providers", ["nvidia"])))
        found = json.loads((out / "discover.json").read_text())["probed"]
        ok = sorted([r for r in found if r["ok"] and r["seconds"] <= float(req.get("auto_max_seconds", 30))], key=lambda r: r["seconds"])
        have = {m.split(":", 1)[-1].split("@")[0] for m in req["models"]}
        extra = [f"{r.get('provider', 'nvidia')}:{r['model']}" for r in ok if r["model"] not in have][: int(req.get("auto_add", 0))]
        req["models"] += extra
        notice("discovered", f"usable {len(ok)}/{len(found)}: " + ", ".join(f"{r.get('provider', 'nvidia')}:{r['model']} ({r['seconds']}s)" for r in ok))
        notice("auto-added models", ", ".join(extra) or "none")
    results = await run_eval.main(req, out)
    lines = []
    for spec, entry in results["models"].items():
        for k, v in entry.items():
            lines.append(f"{spec} {k}: {json.dumps(v['summary'])}")
    (out / "summary.txt").write_text("\n".join(lines))
    for line in lines[:9]:
        notice("eval", line)


if __name__ == "__main__":
    asyncio.run(main())
