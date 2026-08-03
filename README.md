# Resumizer 🚀
### Resume Optimization & AI Career Coach (Multi-Agent RAG System)

Resumizer is an AI-powered resume scoring, tailoring, skill gap analysis, and interview preparation platform built with a multi-agent pipeline.

## 🛠️ Architecture & Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **LLM Provider**: NVIDIA AI Endpoints (`ChatNVIDIA`)
- **Agent Orchestration**: LangChain (LCEL + Pydantic Structured Outputs)
- **Vector Store & RAG**: ChromaDB (`langchain-chroma`)
- **Frontend**: React 18 (Vite, TailwindCSS / CSS Modules, Recharts)

## 🔄 Multi-Agent Pipeline

```
Resume + JD ➔ Parse Agent ➔ ATS Scoring ➔ Skill Gap ➔ Bullet Rewriter ➔ Interview Prep ➔ RAG Career Coach
```

## 📋 Implementation Roadmap
- [x] Repository Setup & Planning
- [ ] Phase 1: Backend Setup, Config & Pydantic Schemas
- [ ] Phase 2: Document Processing & Resume Parser Agent
- [ ] Phase 3: Core Multi-Agent Analysis Pipeline
- [ ] Phase 4: RAG Vector Store & Career Coach Agent
- [ ] Phase 5: FastAPI REST API Endpoints
- [ ] Phase 6: React Frontend UI (Vite)
- [ ] Phase 7: E2E Integration & Walkthrough
