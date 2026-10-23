"""Check which NVIDIA models your API key can use for Resumizer.

    cd backend
    python scripts/check_models.py            # configured chain + common candidates
    python scripts/check_models.py some/model # specific models

Reads NVIDIA_API_KEY from the environment or backend/.env. Prints only model
names, HTTP status, latency and whether the model extracted a test resume
correctly. The key is never printed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app.config import settings  # noqa: E402
from app.llm.provider import NvidiaChatClient, ProviderError  # noqa: E402
from app.llm.structured import extract_json  # noqa: E402

CANDIDATES = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-nano-3-30b-a3b",
    "openai/gpt-oss-20b",
    "mistralai/mistral-large-2-instruct",
    "deepseek-ai/deepseek-v4.1-flash",
    "google/gemma-4-31b-it",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-8b-instruct",
]

RESUME = """Priya Raman
EXPERIENCE
Senior Data Engineer - Halcyon Freight (Mar 2021 - Present)
- Maintain Airflow pipelines that load shipment data into Snowflake.
Data Analyst - Brightwell Insurance (Jul 2018 - Feb 2021)
- Built weekly claims dashboards in Tableau."""

PROMPT = [
    {"role": "system", "content": "Extract resume facts as JSON. Use only facts in the text. Reply with one JSON object."},
    {"role": "user", "content": 'Keys: full_name, jobs (array of {company, job_title, start_date}).\n\n' + RESUME},
]


def check(model: str) -> dict:
    client = NvidiaChatClient(api_key=settings.NVIDIA_API_KEY, models=[model], base_url=settings.NVIDIA_BASE_URL, timeout=90)
    t0 = time.time()
    try:
        out = client._complete_sync(PROMPT, 0.0, 600, True)
    except ProviderError as e:
        return {"model": model, "ok": False, "error": e.kind, "detail": e.message[:120], "seconds": round(time.time() - t0, 1)}
    secs = round(time.time() - t0, 1)
    try:
        data = extract_json(out.text)
        blob = json.dumps(data)
        accurate = all(s in blob for s in ("Priya Raman", "Halcyon Freight", "Senior Data Engineer", "Brightwell Insurance", "Data Analyst"))
    except ValueError:
        accurate = False
    return {"model": model, "ok": True, "accurate_extraction": accurate, "seconds": secs}


def key_shape(key: str) -> str:
    """Describe the key's format without revealing any of it."""
    lines = [l for l in key.splitlines() if l.strip()]
    return (f"length={len(key)}, non-empty lines={len(lines)}, starts with 'nvapi-'={key.startswith('nvapi-')}, "
            f"contains spaces={' ' in key}, contains '='={'=' in key}, "
            f"lines starting with 'nvapi-'={sum(1 for l in lines if l.strip().startswith('nvapi-'))}")


def main(argv):
    if not settings.api_key_configured:
        print("NVIDIA_API_KEY is not set (environment or backend/.env).")
        return 2
    shape = key_shape(settings.NVIDIA_API_KEY)
    print("Key format:", shape)
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::notice title=key format::{shape}")
    try:
        listed = {m["id"] for m in requests.get(f"{settings.NVIDIA_BASE_URL}/models", timeout=20).json().get("data", [])}
    except Exception:
        listed = set()
    models = argv or list(dict.fromkeys(settings.model_chain + CANDIDATES))
    print(f"Configured chain: {', '.join(settings.model_chain)}\n")
    print(f"{'model':45} {'listed':7} {'result':10} {'accurate':9} {'secs':>5}  detail")
    usable = []
    for m in models:
        r = check(m)
        result = "OK" if r["ok"] else r["error"]
        acc = ("yes" if r.get("accurate_extraction") else "no") if r["ok"] else "-"
        print(f"{m:45} {'yes' if m in listed else 'no':7} {result:10} {acc:9} {r['seconds']:>5}  {r.get('detail', '')}")
        if os.getenv("GITHUB_ACTIONS"):
            # Surface results as annotations (readable through the GitHub API).
            print(f"::notice title=model {m}::{result}; accurate={acc}; {r['seconds']}s; listed={'yes' if m in listed else 'no'}; {r.get('detail', '')[:100]}")
        if r["ok"] and r.get("accurate_extraction"):
            usable.append(m)
    print("\nUsable and accurate:", ", ".join(usable) or "none")
    if usable:
        print(f"Suggested settings:\n  NVIDIA_MODEL_NAME={usable[0]}\n  NVIDIA_FALLBACK_MODELS={','.join(usable[1:3])}")
    return 0 if usable else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
