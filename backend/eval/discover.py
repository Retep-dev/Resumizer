"""Which chat models can this NVIDIA key actually use? Prints availability and latency.

    python -m eval.discover --out eval_out
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app.config import settings  # noqa: E402
from app.llm.provider import NvidiaChatClient, ProviderError  # noqa: E402

# Families worth testing for writing quality (instruction-tuned, mid-to-large).
INTERESTING = re.compile(
    r"(gpt-oss|nemotron|qwen3|qwen2\.5-72b|llama-4|llama-3\.3-70b|llama-3\.1-405b|llama-3\.1-70b|mistral-(?:large|medium|small-3)|"
    r"mixtral-8x22b|deepseek|kimi|gemma-(?:3|4)|phi-4|granite-3|glm|minimax|seed-oss|magistral)", re.I)
SKIP = re.compile(r"(embed|rerank|guard|safety|reward|vision|-vl|vlm|parse|retriever|clip|ocr|asr|tts|audio|coder|math|translate|nemoguard|content)", re.I)

PROMPT = [{"role": "user", "content": "Rewrite this resume bullet more strongly without adding facts. Reply with the bullet only.\n"
                                      "Responsible for training new cashiers."}]


async def probe(model: str, timeout: float):
    c = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=[model], base_url=settings.NVIDIA_BASE_URL, timeout=timeout)
    t0 = time.monotonic()
    try:
        out = await c.complete(PROMPT, temperature=0.2, max_tokens=400)
        return {"model": model, "ok": True, "seconds": round(time.monotonic() - t0, 1), "reply": out.text[:160],
                "prompt_tokens": out.prompt_tokens, "completion_tokens": out.completion_tokens}
    except ProviderError as e:
        return {"model": model, "ok": False, "seconds": round(time.monotonic() - t0, 1), "error": e.kind, "detail": e.message[:160]}


async def main(out: Path, timeout: float, limit: int):
    out.mkdir(parents=True, exist_ok=True)
    try:
        listed = sorted(m["id"] for m in requests.get(f"{settings.NVIDIA_BASE_URL}/models", timeout=30).json().get("data", []))
    except Exception as e:
        listed = []
        print("could not list models:", e)
    candidates = [m for m in listed if INTERESTING.search(m) and not SKIP.search(m)][:limit]
    print(f"{len(listed)} models listed; probing {len(candidates)}", flush=True)
    results = []
    for i in range(0, len(candidates), 6):
        batch = await asyncio.gather(*(probe(m, timeout) for m in candidates[i:i + 6]))
        for r in batch:
            print(json.dumps(r), flush=True)
        results += batch
    (out / "discover.json").write_text(json.dumps({"listed": listed, "probed": results}, indent=1))
    ok = [r for r in results if r["ok"]]
    print(f"\nUsable: {len(ok)}/{len(results)}")
    for r in sorted(ok, key=lambda r: r["seconds"]):
        print(f"  {r['model']:55} {r['seconds']:>6}s  {r['reply'][:90]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval_out")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()
    asyncio.run(main(Path(a.out), a.timeout, a.limit))
