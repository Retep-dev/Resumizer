import os
from dotenv import load_dotenv

load_dotenv()


def _csv(value: str):
    return [v.strip() for v in value.split(",") if v.strip()]


# Production defaults: Groq free plan only (the one free provider whose terms allow serving real users).
# Each task leads with a different model because Groq's free quotas are per model. Provisional until the
# Groq evaluation (backend/eval) confirms the choice.
PRODUCTION_CHAINS = {
    # From the Groq evaluation on the 7 fictional resumes (rounds 1b and 2, 29-30 Oct 2026):
    # - gpt-oss-120b: most genuine rewordings with no unsafe rewrites; analysis and interview prep share its quota.
    # - gpt-oss-20b: the most concise, accurate coach (7/7 gap answers, fewest corrections).
    # - qwen3.8-27b: grounded, but its 1,000 output-tokens-per-minute limit refuses interview-length answers,
    #   so it is only the coach's fallback (short replies).
    "analysis": ["groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-20b"],
    "rewrite": ["groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-20b"],
    "interview": ["groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-20b"],
    "coach": ["groq:openai/gpt-oss-20b", "groq:qwen/qwen3.8-27b"],
}


class Settings:
    # Strip whitespace and quotes: keys pasted into secret stores often pick up a
    # trailing newline, which makes the Authorization header invalid.
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "").strip().strip('"').strip("'").strip()
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    # Primary chat model. If NVIDIA reports it as retired/unknown (404/410), the
    # provider moves on to NVIDIA_FALLBACK_MODELS in order and remembers the
    # retirement for the life of the process. Run `python scripts/check_models.py`
    # to verify which models your key can use.
    NVIDIA_MODEL_NAME: str = os.getenv("NVIDIA_MODEL_NAME", "nvidia/nemotron-3.5-lightning-30b-a3b")
    NVIDIA_FALLBACK_MODELS = _csv(os.getenv(
        "NVIDIA_FALLBACK_MODELS",
        "openai/gpt-oss-20b",
    ))
    # ── Free providers only. Resumizer never calls a paid inference API. ──
    # Groq and Cerebras free tiers are used only when their key is set; neither can bill
    # an account that has no payment method attached.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'").strip()
    CEREBRAS_API_KEY: str = os.getenv("CEREBRAS_API_KEY", "").strip().strip('"').strip("'").strip()
    # Kept only so a stray "true" is visible and ignored: there are no paid providers to enable.
    ALLOW_PAID_PROVIDERS_REQUESTED: bool = os.getenv("ALLOW_PAID_PROVIDERS", "false").strip().lower() == "true"
    ALLOW_PAID_PROVIDERS: bool = False
    # Per-task model chains: comma-separated "provider:model" (provider defaults to nvidia).
    # Unset = the default chain for that task (DEFAULT_CHAINS). Example: MODELS_REWRITE="groq:llama-3.3-70b-versatile,nvidia:nvidia/nemotron-3-ultra-550b-a55b"
    TASKS = ("analysis", "rewrite", "interview", "coach")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", str(6 * 3600)))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def api_key_configured(self) -> bool:
        k = self.NVIDIA_API_KEY.strip()
        return bool(k) and "your-key-here" not in k.lower()

    @property
    def model_chain(self):
        chain = [self.NVIDIA_MODEL_NAME] + self.NVIDIA_FALLBACK_MODELS
        seen, out = set(), []
        for m in chain:
            if m and m not in seen:
                seen.add(m)
                out.append(m)
        return out


    def task_chain(self, task: str):
        """[(provider, model)] for a task, in fallback order."""
        raw = os.getenv(f"MODELS_{task.upper()}", "").strip()
        if raw:
            entries = _csv(raw)
        elif os.getenv("AI_DEPLOYMENT", "production").strip().lower() != "evaluation":
            entries = PRODUCTION_CHAINS.get(task, PRODUCTION_CHAINS["analysis"])
        else:
            # Free-only defaults chosen by the writing evaluation (backend/eval). Writing tasks lead with the
            # larger Nemotron model; extraction stays on the fast one. Thinking modes are excluded: they
            # returned empty answers.
            lead = {"rewrite": ["nvidia/nemotron-3-ultra-550b-a55b"], "coach": ["nvidia/nemotron-3-ultra-550b-a55b"]}.get(task, [])
            chain = list(dict.fromkeys(lead + self.model_chain))
            if task == "coach" and "openai/gpt-oss-20b" in chain:
                chain.remove("openai/gpt-oss-20b")
                chain.insert(1, "openai/gpt-oss-20b")
            entries = [f"nvidia:{m}" for m in chain]
        out = []
        for e in entries:
            provider, _, model = e.partition(":") if ":" in e.split("/")[0] else ("nvidia", "", e)
            out.append((provider.strip().lower(), model.strip()))
        return out


settings = Settings()
