# Resumizer 🚀

**AI-powered resume optimization platform built on a multi-agent pipeline.** Upload a resume and a target job description — Resumizer scores your ATS match, identifies skill gaps, rewrites bullet points using the STAR formula, generates tailored interview questions, and provides an AI career coach for follow-up advice — with every result grounded in what your resume actually says.

---

## Architecture

Resumizer runs a **three-stage pipeline**. The uploaded resume is the source of truth: every AI output is checked against it, and nothing the resume doesn't support is shown.

```
  Resume (PDF/DOCX/TXT/MD) + Job description
                    │
  Stage 1 (parallel)├─ Resume parser (AI) ──► grounded against resume text
                    └─ Job analysis (AI) ───► requirements grounded against the posting
                    │
  Stage 2 (code)    └─ ATS score + skill gaps: deterministic, published criteria,
                       every match cites the resume line it came from
                    │
  Stage 3 (parallel)├─ Bullet rewrites (AI) ─► withheld if they add numbers or skills
                    └─ Interview prep (AI) ──► sample answers dropped if they invent facts
                    │
  Career coach (AI) ── sees the full resume, posting and analysis; multi-turn
```

Every response carries a processing status (`complete`, `partial`, `unavailable`) and a per-stage report (`ai`, `rule_based`, `unavailable`). If the AI provider is down, Resumizer falls back to text-grounded rules for parsing, scoring and template interview questions, labels them clearly, and produces **no** rewrites rather than invented ones. If the resume can't be read reliably without the AI, the API returns `503 ai_unavailable` instead of a guess.

### ATS score

`overall = 50% keywords + 30% experience + 20% formatting`, computed in code (`backend/app/agents/scoring.py`):

- **Keywords** — share of the posting's requirements found in the resume (required = 1, preferred = 0.5).
- **Experience** — 70% dated years of experience vs. the posting's minimum, 30% overlap between the posting's title and your job titles.
- **Formatting** — eight ATS-readability checks (name, email, roles, dates, bullets, skills, education, length).

---

## Tech Stack

### Backend

| Tool | Purpose |
|------|---------|
| **Python 3.11** | Runtime |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Request/response validation and LLM structured output schemas |
| **requests** | NVIDIA API Catalog client (OpenAI-compatible `/v1/chat/completions`) with model fallback chain and typed errors |
| **pytest** | Regression tests with a mocked provider, plus an opt-in live test |
| **pdfplumber** | PDF text extraction |
| **python-docx** | DOCX text extraction |
| **python-dotenv** | Environment variable management |
| **python-multipart** | File upload handling |

### Frontend

| Tool | Purpose |
|------|---------|
| **React 18** | UI framework |
| **Vite 5** | Dev server and production bundler |
| **Tailwind CSS 3** | Utility-first styling |
| **Axios** | HTTP client for API requests |
| **react-markdown** | Markdown rendering in career coach chat |
| **clsx** | Conditional className utility |
| **Google Fonts** (Anybody, Atkinson Hyperlegible) | Typography |

### Deployment

| Tool | Purpose |
|------|---------|
| **Render** | Backend hosting (Python web service) |
| **Vercel** | Frontend hosting (static SPA) |

### LLM (free providers only)

Resumizer never calls a paid inference API, and no paid provider exists in the code. Two modes, set by `AI_DEPLOYMENT`:

- **`production` (default):** only providers whose terms allow serving real users' resumes. Today that is Groq's free
  plan (no payment method on the account, so it cannot bill; turn on Zero Data Retention in Groq's data controls).
- **`evaluation`:** also allows NVIDIA's API Catalog trial and Cerebras. NVIDIA's trial terms allow internal testing
  and evaluation only, not production use or personal data, and Cerebras's production rights aren't verified. Use
  fictional resumes only; the upload page shows a warning in this mode.

| Task | Production default chain (Groq free plan) |
|------|-------------------------------------------|
| Analysis (resume parsing, posting requirements) | `openai/gpt-oss-20b` → `qwen/qwen3.8-27b` |
| Rewriting | `openai/gpt-oss-120b` → `qwen/qwen3.8-27b` |
| Interview prep | `openai/gpt-oss-20b` → `qwen/qwen3.8-27b` |
| Coach | `qwen/qwen3.8-27b` → `openai/gpt-oss-120b` |

These are provisional until the Groq evaluation in `backend/eval` confirms them. Groq's free quotas are per model and
per account (about 1,000 requests, 200,000 tokens a day and 8,000 tokens a minute per model), so tasks lead with
different models. The router counts tokens against each model's daily quota and stops at 90%, waits out per-minute
limits, and rests a model for the day when Groq reports its daily limit. When no free model is left, the app returns
its rule-based result or a clear "free AI capacity is used up" error. `/api/v1/status` shows the mode, each task's
chain, its terms note and quota, usage so far, and the limits below with how they were worked out.

## Features

- **ATS Scoring** — Overall match score, keyword match, experience alignment, and formatting scores against a target job description.
- **Skill Gap Analysis** — Identifies matched and missing hard/soft skills with prioritized recommendations.
- **Grounded rewrites** — Clearer bullets in the posting's language; rewrites that add numbers or skills the resume doesn't show are withheld, and you're asked for metrics instead.
- **Interview Prep Generator** — Generates 6 tailored questions (2 behavioral, 2 technical, 2 gap-focused) with STAR-structured sample answers.
- **Career Coach** — Multi-turn chat grounded in the full resume, job description and analysis.
- **Multi-format Upload** — Accepts PDF, DOCX, TXT, and MD resume files.
- **Transparent fallbacks** — If the AI is unavailable, text-grounded rules take over where they're reliable and are labelled as such; anything that needs the AI is withheld, never faked.

---

## Project Structure

```
resumizer/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── pipeline.py                # Multi-agent orchestrator
│   │   │   ├── resume_parser_agent.py     # Stage 1: Raw text → ResumeSchema
│   │   │   ├── ats_scoring_agent.py       # Stage 2: ATS match scoring
│   │   │   ├── skill_gap_agent.py         # Stage 2: Skill gap analysis
│   │   │   ├── resume_rewrite_agent.py    # Stage 3: STAR bullet rewriting
│   │   │   ├── interview_generator_agent.py # Stage 3: Interview question generation
│   │   │   ├── job_analysis_agent.py      # Stage 1: job requirements (separate from resume)
│   │   │   ├── scoring.py                 # Stage 2: deterministic ATS score + gaps
│   │   │   └── career_coach_agent.py      # Grounded multi-turn coach
│   │   ├── schemas/
│   │   │   └── resume.py                  # Pydantic models (ResumeSchema, ATSScore, etc.)
│   │   ├── services/
│   │   │   ├── document_parser.py         # PDF/DOCX/TXT text extraction
│   │   │   ├── session_store.py           # In-memory session context for the coach
│   │   │   └── text_utils.py              # Grounding checks (term matching, numbers, dates)
│   │   ├── llm/                           # NVIDIA client, model fallback, JSON validation
│   │   ├── config.py                      # Environment settings
│   │   └── main.py                        # FastAPI app and endpoints
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                        # StretchType, Wipe (before/after), Toast
│   │   │   ├── Navbar.jsx                 # Header + results tabs
│   │   │   ├── Landing.jsx                # Marketing page
│   │   │   ├── FileUploader.jsx           # Resume upload + JD input with validation
│   │   │   ├── AnalysisProgress.jsx       # Loading state with cancel
│   │   │   ├── ErrorNotice.jsx            # Server / network errors
│   │   │   ├── ATSScoreCard.jsx           # ATS score dashboard
│   │   │   ├── SkillGapView.jsx           # Skill gap visualization
│   │   │   ├── RewriteDiffView.jsx        # Original vs rewritten bullets
│   │   │   ├── InterviewPrep.jsx          # Interview questions display
│   │   │   ├── AnalysisStatus.jsx         # How the analysis was produced
│   │   │   └── CareerCoachChat.jsx        # Coach chat interface
│   │   ├── hooks/                         # useHashRoute, useReducedMotion
│   │   ├── App.jsx                        # Main app: routing, analyze flow, result tabs
│   │   ├── api.js                         # Axios instance configuration
│   │   └── main.jsx                       # React entry point
│   ├── vite.config.js
│   ├── vercel.json
│   └── package.json
├── render.yaml                            # Render deployment config
└── LICENSE                                # MIT
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` / `HEAD` | `/` | Health check |
| `GET` / `HEAD` | `/health` | Health check |
| `GET` | `/api/v1/status` | Configured model chain and any models found retired (no secrets) |
| `POST` | `/api/v1/analyze` | Upload resume file + job description, returns analysis with per-stage status |
| `POST` | `/api/v1/chat` | Message the career coach (multi-turn; optional `analysis` for restarts) |

Errors are `{"detail": {"code": ..., "message": ...}}` with codes `validation_failed` (400), `parsing_failed` (422), `session_expired` (404), `ai_unavailable` (503) and `internal_error` (500).

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [NVIDIA NIM API key](https://build.nvidia.com/)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (or set AI_DEPLOYMENT=evaluation with an NVIDIA key and fictional resumes)
python -m uvicorn app.main:app --reload --port 8000
```

Tests (mocked AI, no key needed): `cd backend && python -m pytest -q`.
Live check against NVIDIA: `python scripts/check_models.py`, then `RESUMIZER_LIVE=1 python -m pytest tests/test_live_nvidia.py -s`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies `/api` requests to the backend on port 8000.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_DEPLOYMENT` | `production` (only providers cleared for real users) or `evaluation` (fictional data only) | `production` |
| `GROQ_API_KEY` | Groq free-plan key (account with no payment method) | — |
| `NVIDIA_API_KEY`, `CEREBRAS_API_KEY` | Evaluation-only keys | — |
| `MODELS_ANALYSIS`, `MODELS_REWRITE`, `MODELS_INTERVIEW`, `MODELS_COACH` | Per-task chain, `provider:model,…` (free providers only) | see above |
| `MODEL_QUOTAS` | The account's real free quotas if they differ from Groq's published ones, e.g. `groq:openai/gpt-oss-120b:rpd=1000:tpd=200000:tpm=8000` | published free plan |
| `QUOTA_HEADROOM` | Share of a model's daily quota to use before stopping | `0.9` |
| `DAILY_REQUEST_CAPS` | Extra request caps per `provider` or `provider:model`, e.g. `groq:900` | none |
| `REWRITE_MODE` | `batch` (1–2 requests per resume) or `single` (one per bullet) | `batch` |
| `ANALYZE_LIMIT_PER_DAY` / `ANALYZE_LIMIT_PER_HOUR` | Analyses per person | `3` / `3` |
| `CHAT_LIMIT_PER_SESSION` / `CHAT_LIMIT_PER_DAY` / `CHAT_LIMIT_PER_HOUR` | Coach messages per analysis / per person per day / per hour | `10` / `20` / `20` |
| `GLOBAL_ANALYZE_LIMIT_PER_DAY` / `GLOBAL_CHAT_LIMIT_PER_DAY` | Whole-app daily caps. Unset = worked out from the free quota and the measured tokens per journey | from quota |
| `JOURNEY_TOKENS`, `EXPECTED_COACH_MESSAGES` | Tokens per stage and coach messages per analysis used to size the global caps | measured values, `4` |
| `MAX_CONCURRENT_ANALYSES` / `MAX_CONCURRENT_CHATS` | Simultaneous requests before "busy". Unset analyses = from the per-minute token limit | from quota / `4` |
| `PIPELINE_TIMEOUT_SECONDS` / `CHAT_TIMEOUT_SECONDS` | Overall request timeouts | `240` / `90` |
| `LLM_TIMEOUT_SECONDS` | Per-request model timeout | `60` |
| `HOST` / `PORT` | Backend bind address | `0.0.0.0` / `8000` |

`ALLOW_PAID_PROVIDERS` has no effect: there is no paid provider in the code.

---

## License

[MIT](LICENSE) © 2026 Afolabi Peter
