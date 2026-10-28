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

Resumizer never calls a paid inference API. Each task has its own chain of free models:

| Task | Default chain |
|------|---------------|
| Analysis (resume parsing, posting requirements) | `nemotron-3.5-lightning-30b-a3b` → `gpt-oss-20b` |
| Rewriting | `nemotron-3-ultra-550b-a55b` → `nemotron-3.5-lightning-30b-a3b` → `gpt-oss-20b` |
| Interview prep | `nemotron-3.5-lightning-30b-a3b` → `gpt-oss-20b` |
| Coach | `nemotron-3-ultra-550b-a55b` → `gpt-oss-20b` → `nemotron-3.5-lightning-30b-a3b` |

Supported providers: `nvidia` (API Catalog trial key), `groq` and `cerebras` (free tiers, used only when their key is set).
**NVIDIA's trial terms allow internal testing and evaluation only, not production use or personal data.** Before
serving real users, move the chains to a provider whose terms allow it (see `/api/v1/status`, which shows each
provider's terms note). Models that fail repeatedly are cooled down; when no free model is available the app
returns its rule-based result or a clear error. Choices are backed by `backend/eval` (see its request file).

-------|----------|
| `nvidia/nemotron-3-super-120b-a12b` (default) | NVIDIA API Catalog |
| `nvidia/nemotron-3.5-lightning-30b-a3b`, `openai/gpt-oss-20b` (fallbacks) | NVIDIA API Catalog |

Models are configurable. If a model is retired the client moves to the next one automatically. Check what your key can use with `python backend/scripts/check_models.py`.

---

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
# Edit .env and add your NVIDIA_API_KEY
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
| `NVIDIA_API_KEY` | NVIDIA API Catalog key (trial: evaluation only) | — |
| `GROQ_API_KEY`, `CEREBRAS_API_KEY` | Optional free-tier keys (accounts with no payment method) | — |
| `NVIDIA_MODEL_NAME`, `NVIDIA_FALLBACK_MODELS` | Fast model chain used by analysis and interview prep | `nemotron-3.5-lightning-30b-a3b`, `gpt-oss-20b` |
| `MODELS_ANALYSIS`, `MODELS_REWRITE`, `MODELS_INTERVIEW`, `MODELS_COACH` | Per-task chain, `provider:model,…` (free providers only) | see above |
| `DAILY_REQUEST_CAPS` | Requests per UTC day per `provider` or `provider:model`, to stay inside free quotas, e.g. `groq:900` | none |
| `REWRITE_MODE` | `batch` (1–2 requests per resume) or `single` (one per bullet) | `batch` |
| `ANALYZE_LIMIT_PER_HOUR` / `ANALYZE_LIMIT_PER_DAY` | Analyses per client | `5` / `15` |
| `CHAT_LIMIT_PER_HOUR` / `CHAT_LIMIT_PER_SESSION` | Coach messages per client / per analysis | `40` / `30` |
| `GLOBAL_ANALYZE_LIMIT_PER_DAY` / `GLOBAL_CHAT_LIMIT_PER_DAY` | Whole-app daily caps | `300` / `2000` |
| `MAX_CONCURRENT_ANALYSES` / `MAX_CONCURRENT_CHATS` | Simultaneous requests before "busy" | `3` / `6` |
| `PIPELINE_TIMEOUT_SECONDS` / `CHAT_TIMEOUT_SECONDS` | Overall request timeouts | `180` / `90` |
| `LLM_TIMEOUT_SECONDS` | Per-request model timeout | `60` |
| `HOST` / `PORT` | Backend bind address | `0.0.0.0` / `8000` |

`ALLOW_PAID_PROVIDERS` has no effect: there is no paid provider in the code.

----------|-------------|---------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key (required) | — |
| `NVIDIA_MODEL_NAME` | Primary chat model | `nvidia/nemotron-3-super-120b-a12b` |
| `NVIDIA_FALLBACK_MODELS` | Comma-separated models tried in order if the primary is retired | `nvidia/nemotron-3.5-lightning-30b-a3b,openai/gpt-oss-20b` |
| `LLM_TIMEOUT_SECONDS` | Per-request model timeout | `60` |
| `HOST` | Backend bind host | `0.0.0.0` |
| `PORT` | Backend bind port | `8000` |

---

## License

[MIT](LICENSE) © 2026 Afolabi Peter
