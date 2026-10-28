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
from app.llm.provider import ProviderError  # noqa: E402
from app.llm.router import FREE_PROVIDERS, provider_client, provider_status  # noqa: E402
import dataclasses  # noqa: E402

# Families worth testing for writing quality (instruction-tuned, mid-to-large).
INTERESTING = re.compile(
    r"(gpt-oss|nemotron|qwen3|qwen2\.5-72b|llama-4|llama-3\.3-70b|llama-3\.1-405b|llama-3\.1-70b|mistral-(?:large|medium|small-3)|"
    r"mixtral-8x22b|deepseek|kimi|gemma-(?:3|4)|phi-4|granite-3|glm|minimax|seed-oss|magistral)", re.I)
SKIP = re.compile(r"(embed|rerank|guard|safety|reward|vision|-vl|vlm|parse|retriever|clip|ocr|asr|tts|audio|coder|math|translate|nemoguard|content)", re.I)

PROMPT = [{"role": "user", "content": "Rewrite this resume bullet more strongly without adding facts. Reply with the bullet only.\n"
                                      "Responsible for training new cashiers."}]


async def probe(model: str, timeout: float, provider: str = "nvidia"):
    c = dataclasses.replace(provider_client(provider), models=[model], timeout=timeout)
    t0 = time.monotonic()
    try:
        out = await c.complete(PROMPT, temperature=0.2, max_tokens=400)
        return {"provider": provider, "model": model, "ok": True, "seconds": round(time.monotonic() - t0, 1), "reply": out.text[:160],
                "prompt_tokens": out.prompt_tokens, "completion_tokens": out.completion_tokens}
    except ProviderError as e:
        return {"provider": provider, "model": model, "ok": False, "seconds": round(time.monotonic() - t0, 1), "error": e.kind, "detail": e.message[:160]}


async def main(out: Path, timeout: float, limit: int, providers=("nvidia",)):
    out.mkdir(parents=True, exist_ok=True)
    listed_all, results = {}, []
    for provider in providers:
        if not provider_status(provider)[0]:
            print(f"{provider}: skipped ({provider_status(provider)[1]})")
            continue
        base = settings.NVIDIA_BASE_URL if provider == "nvidia" else FREE_PROVIDERS[provider]["base"]
        key = provider_client(provider).api_key
        try:
            data = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30).json().get("data", [])
            listed = sorted(m["id"] for m in data)
        except Exception as e:
            listed = []
            print(f"{provider}: could not list models: {type(e).__name__}")
        listed_all[provider] = listed
        candidates = [m for m in listed if (provider != "nvidia" or INTERESTING.search(m)) and not SKIP.search(m)][:limit]
        print(f"{provider}: {len(listed)} models listed; probing {len(candidates)}", flush=True)
        for i in range(0, len(candidates), 4):
            batch = await asyncio.gather(*(probe(m, timeout, provider) for m in candidates[i:i + 4]))
            for r in batch:
                print(json.dumps(r), flush=True)
            results += batch
    (out / "discover.json").write_text(json.dumps({"listed": listed_all, "probed": results}, indent=1))
    ok = [r for r in results if r["ok"]]
    print(f"\nUsable: {len(ok)}/{len(results)}")
    for r in sorted(ok, key=lambda r: r["seconds"]):
        print(f"  {r['provider']}:{r['model']:50} {r['seconds']:>6}s  {r['reply'][:80]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval_out")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()
    asyncio.run(main(Path(a.out), a.timeout, a.limit, tuple(FREE_PROVIDERS)))
