# Resumizer 🚀

**AI-powered resume optimization platform built on a multi-agent pipeline.** Upload a resume and a target job description — Resumizer scores your ATS match, identifies skill gaps, rewrites bullet points using the STAR formula, generates tailored interview questions, and provides a RAG-powered AI career coach for follow-up advice.

---

## Architecture

Resumizer uses a **3-stage parallel multi-agent pipeline** orchestrated with LangChain LCEL. Each agent is backed by an NVIDIA NIM LLM endpoint with Pydantic structured output, and includes an algorithmic fallback if the LLM is unavailable.

```
                         ┌──────────────────┐
  Resume (PDF/DOCX/TXT)  │   Stage 1        │
  + Job Description ────►│   Resume Parser   │
                         │   Agent           │
                         └────────┬─────────┘
                                  │ ResumeSchema
                    ┌─────────────┴─────────────┐
                    ▼                             ▼
           ┌────────────────┐            ┌────────────────┐
  Stage 2  │ ATS Scoring    │            │ Skill Gap      │
 (parallel)│ Agent          │            │ Analysis Agent │
           └───────┬────────┘            └───────┬────────┘
                   │                             │
                   └─────────────┬───────────────┘
                    ┌────────────┴────────────┐
                    ▼                          ▼
           ┌────────────────┐         ┌────────────────┐
  Stage 3  │ STAR Bullet    │         │ Interview Prep │
 (parallel)│ Rewriter Agent │         │ Generator Agent│
           └───────┬────────┘         └───────┬────────┘
                   │                           │
                   └───────────┬───────────────┘
                               ▼
                      ┌────────────────┐
                      │ RAG Career     │
                      │ Coach Agent    │◄── ChromaDB vector store
                      └────────────────┘
```

---

## Tech Stack

### Backend

| Tool | Purpose |
|------|---------|
| **Python 3.11** | Runtime |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Request/response validation and LLM structured output schemas |
| **LangChain** | Agent orchestration (LCEL chains, prompt templates, structured output) |
| **langchain-nvidia-ai-endpoints** | `ChatNVIDIA` LLM client and `NVIDIAEmbeddings` for vector embeddings |
| **ChromaDB** (via `langchain-chroma`) | Local vector store for RAG-based career coach |
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
| **Lucide React** | Icon library |
| **react-markdown** | Markdown rendering in career coach chat |
| **clsx** | Conditional className utility |
| **Google Fonts** (Inter, Outfit) | Typography |

### Deployment

| Tool | Purpose |
|------|---------|
| **Render** | Backend hosting (Python web service) |
| **Vercel** | Frontend hosting (static SPA) |

### LLM

| Model | Provider |
|-------|----------|
| `meta/llama-3.1-8b-instruct` (default) | NVIDIA NIM API |
| `meta/llama-3.3-70b-instruct` (optional) | NVIDIA NIM API |
| `nvidia/nv-embedqa-e5-v5` | NVIDIA NIM API (RAG embeddings) |

---

## Features

- **ATS Scoring** — Overall match score, keyword match, experience alignment, and formatting scores against a target job description.
- **Skill Gap Analysis** — Identifies matched and missing hard/soft skills with prioritized recommendations.
- **STAR Bullet Rewriter** — Rewrites resume bullet points using the STAR/XYZ formula, injects missing keywords, and quantifies impact.
- **Interview Prep Generator** — Generates 6 tailored questions (2 behavioral, 2 technical, 2 gap-focused) with STAR-structured sample answers.
- **RAG Career Coach** — Conversational AI chat grounded in the candidate's resume and job description via ChromaDB retrieval.
- **Multi-format Upload** — Accepts PDF, DOCX, TXT, and MD resume files.
- **Algorithmic Fallbacks** — Every agent has a regex/heuristic fallback that activates if the LLM API is unavailable, ensuring the pipeline always returns results.

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
│   │   │   └── career_coach_agent.py      # RAG-powered conversational coach
│   │   ├── schemas/
│   │   │   └── resume.py                  # Pydantic models (ResumeSchema, ATSScore, etc.)
│   │   ├── services/
│   │   │   ├── document_parser.py         # PDF/DOCX/TXT text extraction
│   │   │   └── rag_service.py             # ChromaDB indexing and retrieval
│   │   ├── config.py                      # Environment settings
│   │   └── main.py                        # FastAPI app and endpoints
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── FileUploader.jsx           # Resume upload + JD input
│   │   │   ├── ATSScoreCard.jsx           # ATS score dashboard
│   │   │   ├── SkillGapView.jsx           # Skill gap visualization
│   │   │   ├── RewriteDiffView.jsx        # Original vs rewritten bullets
│   │   │   ├── InterviewPrep.jsx          # Interview questions display
│   │   │   └── CareerCoachChat.jsx        # RAG chat interface
│   │   ├── App.jsx                        # Main app with tab navigation
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
| `POST` | `/api/v1/analyze` | Upload resume file + job description, returns full analysis |
| `POST` | `/api/v1/chat` | Send a message to the RAG career coach |

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
| `NVIDIA_API_KEY` | NVIDIA NIM API key (required) | — |
| `NVIDIA_MODEL_NAME` | LLM model identifier | `meta/llama-3.3-70b-instruct` |
| `CHROMA_DB_DIR` | ChromaDB persistence directory | `./chroma_db` |
| `HOST` | Backend bind host | `0.0.0.0` |
| `PORT` | Backend bind port | `8000` |

---

## License

[MIT](LICENSE) © 2026 Afolabi Peter
