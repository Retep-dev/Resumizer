import os
from dotenv import load_dotenv

load_dotenv()


def _csv(value: str):
    return [v.strip() for v in value.split(",") if v.strip()]


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
    # ── Optional additional providers (all off unless a key is set AND paid use is allowed) ──
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"').strip("'").strip()
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'").strip()
    # Safety switch: providers other than NVIDIA are never called unless this is "true".
    ALLOW_PAID_PROVIDERS: bool = os.getenv("ALLOW_PAID_PROVIDERS", "false").strip().lower() == "true"
    # Per-task model chains: comma-separated "provider:model" (provider defaults to nvidia).
    # Unset = the NVIDIA chain above. Example: MODELS_REWRITE="anthropic:claude-haiku-4-5,nvidia:nvidia/nemotron-3.5-lightning-30b-a3b"
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
        entries = _csv(raw) if raw else [f"nvidia:{m}" for m in self.model_chain]
        out = []
        for e in entries:
            provider, _, model = e.partition(":") if ":" in e.split("/")[0] else ("nvidia", "", e)
            out.append((provider.strip().lower(), model.strip()))
        return out


settings = Settings()
